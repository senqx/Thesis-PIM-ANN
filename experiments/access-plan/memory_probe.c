/* Minimal contiguous MRAM read throughput probe, with checked final output. */
#include <stdint.h>
#include <defs.h>
#include <mram.h>
__host uint32_t DPU_INPUT_ARGUMENTS[4];
__dma_aligned uint32_t buffers[NR_TASKLETS][TRANSFER_BYTES/4];
int main(void) {
    unsigned tid=me();
    __mram_ptr uint8_t *heap=(__mram_ptr uint8_t *)DPU_MRAM_HEAP_POINTER;
    for (unsigned i=0;i<DPU_INPUT_ARGUMENTS[0];++i) {
        mram_read(heap+(i*NR_TASKLETS+tid)*TRANSFER_BYTES,buffers[tid],TRANSFER_BYTES);
    }
    mram_write(buffers[tid],heap+DPU_INPUT_ARGUMENTS[1]+tid*TRANSFER_BYTES,TRANSFER_BYTES);
    return 0;
}
