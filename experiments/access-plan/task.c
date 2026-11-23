/* Compact, precomputed access-plan feasibility kernel. Integer sum aggregation.
 * MODE 0: stream, 1: runtime direct map, 2: encoded plan.
 * A 32-bit plan word: bit31=load, bits9..30=source id, bits0..8=WRAM offset.
 * Plans are constructed for the exact tasklet partition; each starts empty.
 */
#include <stdint.h>
#include <defs.h>
#include <mram.h>
#ifndef MODE
#define MODE 0
#endif
#ifndef FEATURE_BYTES
#define FEATURE_BYTES 64
#endif
#ifndef INDEX_BYTES
#define INDEX_BYTES 128
#endif
#ifndef INDEX_BITS
#define INDEX_BITS 32
#endif
#if INDEX_BITS == 16
typedef uint16_t index_t;
#else
typedef uint32_t index_t;
#endif
#define INDEX_COUNT (INDEX_BYTES / sizeof(index_t))
#define WORDS (FEATURE_BYTES / 4)
#define SLOTS (512 / FEATURE_BYTES)
__host uint32_t DPU_INPUT_ARGUMENTS[4]; /* refs, features, output, reserved */
typedef struct {
    index_t index[INDEX_COUNT];
#if MODE != 0
    uint32_t retained[512 / 4];
#endif
#if MODE == 1
    uint32_t tags[SLOTS];
#endif
    uint32_t scratch[WORDS];
    uint32_t sum[WORDS];
#if MODE == 3
    uint32_t header[2];
#endif
} workspace;
__dma_aligned workspace spaces[NR_TASKLETS];

#if MODE == 3
#if FEATURE_BYTES != 8 || INDEX_BYTES != 256
#error Batch prototype requires 8-byte features and a 256-byte metadata buffer
#endif
int main(void) {
    unsigned tid = me();
    workspace *w = &spaces[tid];
    __mram_ptr uint8_t *heap = (__mram_ptr uint8_t *)DPU_MRAM_HEAP_POINTER;
    unsigned count = DPU_INPUT_ARGUMENTS[0] / NR_TASKLETS;
    unsigned first = tid * count;
    unsigned cursor = tid * DPU_INPUT_ARGUMENTS[3];
    for (unsigned pos = 0; pos < count; pos += 64) {
        mram_read(heap + cursor, w->header, 8);
        unsigned unique = w->header[0];
        unsigned id_bytes = (unique * 4 + 7) & ~7u;
        cursor += 8;
        mram_read(heap + cursor, w->index, id_bytes);
        cursor += id_bytes;
        for (unsigned u = 0; u < unique; ++u) {
            mram_read(heap + DPU_INPUT_ARGUMENTS[1] + w->index[u] * 8,
                      w->retained + u * 2, 8);
        }
        mram_read(heap + cursor, w->index, 64);
        cursor += 64;
        uint8_t *slots = (uint8_t *)w->index;
        for (unsigned j = 0; j < 64; j += 8) {
            for (unsigned f = 0; f < WORDS; ++f) w->sum[f] = 0;
            for (unsigned k = 0; k < 8; ++k) {
                uint32_t *row = w->retained + slots[j + k] * WORDS;
                for (unsigned f = 0; f < WORDS; ++f) w->sum[f] += row[f];
            }
            mram_write(w->sum, heap + DPU_INPUT_ARGUMENTS[2] + ((first + pos + j) >> 3) * FEATURE_BYTES, FEATURE_BYTES);
        }
    }
    return 0;
}
#else
int main(void) {
    unsigned tid = me();
    workspace *w = &spaces[tid];
    __mram_ptr uint8_t *heap = (__mram_ptr uint8_t *)DPU_MRAM_HEAP_POINTER;
    unsigned count = DPU_INPUT_ARGUMENTS[0] / NR_TASKLETS;
    unsigned first = tid * count;
    unsigned features = DPU_INPUT_ARGUMENTS[1];
    unsigned output = DPU_INPUT_ARGUMENTS[2];
#if MODE == 1
    for (unsigned s = 0; s < SLOTS; ++s) w->tags[s] = 0xffffffffu;
#endif
    for (unsigned pos = 0; pos < count; pos += INDEX_COUNT) {
        unsigned n = INDEX_COUNT;
        if (n > count - pos) n = count - pos;
        mram_read(heap + (first + pos) * sizeof(index_t), w->index, n * sizeof(index_t));
        for (unsigned j = 0; j < n; j += 8) {
            for (unsigned f = 0; f < WORDS; ++f) w->sum[f] = 0;
            for (unsigned k = 0; k < 8; ++k) {
                unsigned token = w->index[j + k];
                uint32_t *row;
#if MODE == 0
                row = w->scratch;
                mram_read(heap + features + token * FEATURE_BYTES, row, FEATURE_BYTES);
#elif MODE == 1
                unsigned slot = token & (SLOTS - 1);
                row = w->retained + slot * WORDS;
                if (w->tags[slot] != token) {
                    w->tags[slot] = token;
                    mram_read(heap + features + token * FEATURE_BYTES, row, FEATURE_BYTES);
                }
#else
                row = (uint32_t *)((uint8_t *)w->retained + (token & 511));
                if ((int32_t)token < 0) {
                    unsigned id = (token & 0x7fffffff) >> 9;
                    mram_read(heap + features + id * FEATURE_BYTES, row, FEATURE_BYTES);
                }
#endif
                for (unsigned f = 0; f < WORDS; ++f) w->sum[f] += row[f];
            }
            mram_write(w->sum, heap + output + ((first + pos + j) >> 3) * FEATURE_BYTES, FEATURE_BYTES);
        }
    }
    return 0;
}
#endif
