#include "memory/address_emitter.h"

#include <cstdio>

#include "layout/memory_layout.h"

namespace pimann {

uint64_t AddressEmitter::addressOf(const AccessRecord& record) const {
  switch (record.kind) {
    case AccessKind::Vector: {
      // Vectors are the region the layout permutes: a node's physical slot
      // decides which DRAM row its payload lands in. vectorStride equals the
      // record span (one full vector).
      const uint64_t slot = m_layout.slotOf(record.nodeId);
      return m_plan.vectorBase + slot * record.byteSpan;
    }
    case AccessKind::Adjacency:
      // Adjacency / metadata keep their own regions and are not yet permuted;
      // a dedicated layout for them is future work (the emitter would take a
      // second mapping). Addressed by node id for now.
      return m_plan.adjacencyBase + record.nodeId * m_plan.adjacencyStride;
    case AccessKind::Metadata:
      return m_plan.metadataBase + record.nodeId * m_plan.metadataStride;
    case AccessKind::Candidate:
      // Search scratch structures live off the modelled data regions; skipped
      // by emit(), handled here only for switch exhaustiveness.
      return 0;
  }
  return 0;
}

uint64_t AddressEmitter::emit(
    const AccessTrace& trace, std::ostream& r_out) const {
  uint64_t records = 0;
  char line[32];
  for (const AccessRecord& record : trace) {
    if (record.kind == AccessKind::Candidate) {
      continue;  // not a modelled DRAM region
    }
    const uint64_t base = addressOf(record);
    // Expand the payload into burst-sized cache-line requests, matching how the
    // controller issues DRAM reads.
    for (uint32_t off = 0; off < record.byteSpan; off += m_plan.burst) {
      const int len = std::snprintf(
          line, sizeof(line), "LD 0x%llx\n",
          static_cast<unsigned long long>(base + off));
      r_out.write(line, len);
      records++;
    }
  }
  return records;
}

}  // namespace pimann
