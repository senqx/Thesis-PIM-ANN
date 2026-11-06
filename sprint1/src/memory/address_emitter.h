#ifndef PIMANN_MEMORY_ADDRESS_EMITTER_H
#define PIMANN_MEMORY_ADDRESS_EMITTER_H

#include <cstdint>
#include <ostream>

#include "memory/access_record.h"

namespace pimann {

class MemoryLayout;

/// Byte-address plan for the three co-resident data regions. Vectors,
/// adjacency lists, and metadata each occupy their own contiguous region so a
/// layout can co-locate one region without perturbing the others.
struct AddressPlan {
  uint64_t vectorBase = 0x10000000;     ///< start of vector-storage region
  uint64_t adjacencyBase = 0x40000000;  ///< start of adjacency region
  uint64_t metadataBase = 0x60000000;   ///< start of metadata region
  uint32_t adjacencyStride = 64;        ///< bytes reserved per node's edges
  uint32_t metadataStride = 16;         ///< bytes reserved per node's metadata
  uint32_t burst = 64;                  ///< cache-line / DRAM burst size
};

/// Translates a layout-independent AccessTrace into the concrete
/// "LD 0x<addr>" lines Ramulator's LoadStoreTrace front-end consumes.
///
/// The physical address of a Vector access depends on the layout (slotOf);
/// Adjacency/Metadata use the node id directly for now (their own layout is
/// future work). Each logical payload is expanded into @ref AddressPlan::burst
/// -sized bursts, matching how the real hardware issues cache-line requests.
class AddressEmitter {
public:
  AddressEmitter(const MemoryLayout& layout, AddressPlan plan)
      : m_layout(layout), m_plan(std::move(plan)) {}

  /// Write the full trace as Ramulator LD records to @p r_out. Returns the
  /// number of burst-level records emitted.
  uint64_t emit(const AccessTrace& trace, std::ostream& r_out) const;

private:
  /// Byte address of a single logical access, before burst expansion.
  uint64_t addressOf(const AccessRecord& record) const;

  const MemoryLayout& m_layout;
  AddressPlan m_plan;
};

}  // namespace pimann

#endif  // PIMANN_MEMORY_ADDRESS_EMITTER_H
