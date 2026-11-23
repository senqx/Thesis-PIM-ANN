/* Immutable, unweighted neighbor-feature aggregation. Eight neighbors/node,
 * 16 uint32 features. No floating-point or trained GNN claim.
 * POLICY: 0 streaming, 1 direct-mapped, 2 degree admission, 3 static degree,
 * 4 four-row blocks, 5 sixteen-row clusters, 6 periodic adaptive allocation.
 */
#include <stdint.h>
#include <defs.h>
#include <mram.h>
#ifndef POLICY
#define POLICY 0
#endif
#ifndef INDEX_BYTES
#define INDEX_BYTES 128
#endif
#define VERTICES 128
#define SLOTS 32
__host uint32_t DPU_INPUT_ARGUMENTS[4]; /* refs, feature offset, metadata, output */
typedef struct {
    uint32_t arena[640]; /* index buffer [0,512); retention [512,2560) */
    uint32_t tags[SLOTS];
    uint32_t metadata[VERTICES];
    uint32_t scratch[16];
    uint32_t sum[16];
} workspace;
__dma_aligned workspace spaces[NR_TASKLETS]; /* 3328 bytes/tasklet */

int main(void) {
    unsigned tid = me();
    workspace *w = &spaces[tid];
    __mram_ptr uint8_t *heap = (__mram_ptr uint8_t *) DPU_MRAM_HEAP_POINTER;
    unsigned count = DPU_INPUT_ARGUMENTS[0] / NR_TASKLETS;
    unsigned first = tid * count;
    unsigned features = DPU_INPUT_ARGUMENTS[1];
    unsigned output = DPU_INPUT_ARGUMENTS[3];
    uint32_t *cache = w->arena + 128;
    for (unsigned i = 0; i < SLOTS; ++i) w->tags[i] = 0xffffffffu;
    for (unsigned i = 0; i < 16; ++i) w->sum[i] = 0;
#if POLICY == 2 || POLICY == 3
    mram_read(heap + DPU_INPUT_ARGUMENTS[2], w->metadata, sizeof(w->metadata));
#endif
#if POLICY == 3
    for (unsigned id = 0; id < VERTICES; ++id) {
        unsigned slot = w->metadata[id];
        if (slot < SLOTS) mram_read(heap + features + id * 64, cache + slot * 16, 64);
    }
#endif
    unsigned pos = 0;
#if POLICY == 6
    unsigned hits = 0, retain = 1;
#endif
    while (pos < count) {
        unsigned n = INDEX_BYTES / 4;
#if POLICY == 6
        if ((pos & 255) == 0) {
            if (!retain) {
                for (unsigned s = 0; s < SLOTS; ++s) w->tags[s] = 0xffffffffu;
            }
            hits = 0;
            retain = 1;
        } else if ((pos & 255) == 32) {
            retain = hits >= 4; /* predeclared 12.5% probe hit threshold */
        }
        n = retain ? 32 : 224; /* bypass reuses former retention storage */
#endif
        if (n > count - pos) n = count - pos;
        mram_read(heap + (first + pos) * 4, w->arena, n * 4);
        for (unsigned j = 0; j < n; ++j) {
            unsigned id = w->arena[j];
            uint32_t *row = w->scratch;
#if POLICY == 0
            mram_read(heap + features + id * 64, row, 64);
#elif POLICY == 3
            unsigned slot = w->metadata[id];
            if (slot < SLOTS) row = cache + slot * 16;
            else mram_read(heap + features + id * 64, row, 64);
#elif POLICY == 4 || POLICY == 5
#if POLICY == 4
            unsigned block = id >> 2, slot = block & 7;
            row = cache + slot * 64;
            if (w->tags[slot] != block) {
                mram_read(heap + features + block * 256, row, 256);
                w->tags[slot] = block;
            }
            row += (id & 3) * 16;
#else
            unsigned block = id >> 4, slot = block & 1;
            row = cache + slot * 256;
            if (w->tags[slot] != block) {
                mram_read(heap + features + block * 1024, row, 1024);
                w->tags[slot] = block;
            }
            row += (id & 15) * 16;
#endif
#else
            unsigned slot = id & (SLOTS - 1);
#if POLICY == 6
            if (!retain) {
                mram_read(heap + features + id * 64, row, 64);
            } else
#endif
            if (w->tags[slot] == id) {
                row = cache + slot * 16;
#if POLICY == 6
                ++hits;
#endif
            } else {
                unsigned admit = 1;
#if POLICY == 2
                admit = w->tags[slot] == 0xffffffffu ||
                    w->metadata[id] >= w->metadata[w->tags[slot]];
#endif
                if (admit) { row = cache + slot * 16; w->tags[slot] = id; }
                mram_read(heap + features + id * 64, row, 64);
            }
#endif
            for (unsigned f = 0; f < 16; ++f) w->sum[f] += row[f];
            if (((pos + j) & 7) == 7) {
                mram_write(w->sum, heap + output + ((first + pos + j) >> 3) * 64, 64);
                for (unsigned f = 0; f < 16; ++f) w->sum[f] = 0;
            }
        }
        pos += n;
    }
    return 0;
}
