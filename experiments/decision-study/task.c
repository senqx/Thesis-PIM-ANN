/* Standard integer CSR SpMV/SpMM and matched local-reuse controls.
 * Weighted contributions; no sampling, approximation or dropped edges.
 * MODE 0 stream, 1 frequency-ordered partial residency, 2 full residency,
 * 3 dictionary batches, 4 BCSR with BLOCK rows and columns.
 * All schedules assign groups of four output rows round-robin to tasklets. */
#include <stdint.h>
#include <defs.h>
#include <mram.h>
#include <barrier.h>
#ifndef MODE
#define MODE 0
#endif
#ifndef WORDS
#define WORDS 2
#endif
#ifndef FEATURE_BYTES
#define FEATURE_BYTES 8
#endif
#ifndef INDEX_BYTES
#define INDEX_BYTES 512
#endif
#ifndef RESIDENT_BYTES
#define RESIDENT_BYTES 24576
#endif
#ifndef BLOCK
#define BLOCK 4
#endif
#define STRIDE (FEATURE_BYTES/4)
__host uint32_t DPU_INPUT_ARGUMENTS[8];
typedef struct {
    uint32_t ptr[8];
    uint32_t sum[4*STRIDE];
#if MODE == 3
    uint32_t header[2];
    uint32_t ids[64];
    uint32_t weights[64];
    uint8_t slots[64];
    uint32_t values[512/4];
#elif MODE == 4
    uint32_t header[2];
    uint32_t weights[BLOCK*BLOCK];
    uint32_t values[BLOCK*STRIDE];
#else
    uint32_t pairs[INDEX_BYTES/4];
    uint32_t scratch[STRIDE];
#endif
} workspace;
__dma_aligned workspace spaces[NR_TASKLETS];
#if MODE == 1 || MODE == 2
__dma_aligned uint32_t resident[RESIDENT_BYTES/4];
BARRIER_INIT(ready, NR_TASKLETS);
#endif
int main(void) {
    unsigned tid=me(); workspace *w=&spaces[tid];
    __mram_ptr uint8_t *heap=(__mram_ptr uint8_t *)DPU_MRAM_HEAP_POINTER;
    unsigned rows=DPU_INPUT_ARGUMENTS[0], cols=DPU_INPUT_ARGUMENTS[1];
    unsigned features=DPU_INPUT_ARGUMENTS[3], output=DPU_INPUT_ARGUMENTS[4];
#if MODE == 1 || MODE == 2
    unsigned hot=DPU_INPUT_ARGUMENTS[5];
    for(unsigned pos=tid*2048;pos<hot*FEATURE_BYTES;pos+=NR_TASKLETS*2048){
        unsigned bytes=hot*FEATURE_BYTES-pos; if(bytes>2048)bytes=2048;
        mram_read(heap+features+pos,(uint8_t*)resident+pos,bytes);
    }
    barrier_wait(&ready);
#endif
    for(unsigned first=tid*4;first<rows;first+=NR_TASKLETS*4){
        for(unsigned f=0;f<4*STRIDE;f++)w->sum[f]=0;
#if MODE <= 2
        mram_read(heap+first*4,w->ptr,32);
        unsigned pairs_base=((rows+1)*4+31)&~31u;
        for(unsigned r=0;r<4;r++){
            for(unsigned p=w->ptr[r];p<w->ptr[r+1];){
                unsigned n=w->ptr[r+1]-p;if(n>INDEX_BYTES/8)n=INDEX_BYTES/8;
                mram_read(heap+pairs_base+p*8,w->pairs,n*8);
                for(unsigned j=0;j<n;j++){
                    unsigned id=w->pairs[2*j], weight=w->pairs[2*j+1];
                    uint32_t *v;
#if MODE == 2
                    v=resident+id*STRIDE;
#elif MODE == 1
                    if(id<hot)v=resident+id*STRIDE;
                    else{v=w->scratch;mram_read(heap+features+id*FEATURE_BYTES,v,FEATURE_BYTES);}
#else
                    v=w->scratch;mram_read(heap+features+id*FEATURE_BYTES,v,FEATURE_BYTES);
#endif
                    for(unsigned f=0;f<WORDS;f++)w->sum[r*STRIDE+f]+=weight*v[f];
                }
                p+=n;
            }
        }
#elif MODE == 3
        unsigned g=first/4;
        mram_read(heap+(g&~1u)*4,w->ptr,16);
        unsigned cursor=w->ptr[g&1], end=w->ptr[(g&1)+1];
        while(cursor<end){
            mram_read(heap+cursor,w->header,8);cursor+=8;
            unsigned u=w->header[0],n=w->header[1];
            unsigned bytes=(u*4+7)&~7u;
            mram_read(heap+cursor,w->ids,bytes);cursor+=bytes;
            for(unsigned j=0;j<u;j++)mram_read(heap+features+w->ids[j]*FEATURE_BYTES,w->values+j*STRIDE,FEATURE_BYTES);
            bytes=(n*4+7)&~7u;
            mram_read(heap+cursor,w->weights,bytes);cursor+=bytes;
            bytes=(n+7)&~7u;
            mram_read(heap+cursor,w->slots,bytes);cursor+=bytes;
            for(unsigned j=0;j<n;j++){
                unsigned r=w->slots[j]>>6,slot=w->slots[j]&63;
                for(unsigned f=0;f<WORDS;f++)w->sum[r*STRIDE+f]+=w->weights[j]*w->values[slot*STRIDE+f];
            }
        }
#else
        for(unsigned rr=0;rr<4;rr+=BLOCK){
            unsigned g=(first+rr)/BLOCK;
            mram_read(heap+(g&~1u)*4,w->ptr,16);
            unsigned cursor=w->ptr[g&1],end=w->ptr[(g&1)+1];
            while(cursor<end){
                mram_read(heap+cursor,w->header,8);cursor+=8;
                mram_read(heap+cursor,w->weights,BLOCK*BLOCK*4);cursor+=BLOCK*BLOCK*4;
                mram_read(heap+features+w->header[0]*FEATURE_BYTES,w->values,BLOCK*FEATURE_BYTES);
                for(unsigned r=0;r<BLOCK;r++)for(unsigned c=0;c<BLOCK;c++){
                    unsigned weight=w->weights[r*BLOCK+c];
                    if(weight)for(unsigned f=0;f<WORDS;f++)w->sum[(rr+r)*STRIDE+f]+=weight*w->values[c*STRIDE+f];
                }
            }
        }
#endif
        mram_write(w->sum,heap+output+first*FEATURE_BYTES,4*FEATURE_BYTES);
    }
    return 0;
}
