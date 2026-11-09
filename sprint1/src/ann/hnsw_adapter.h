#ifndef PIMANN_ANN_HNSW_ADAPTER_H
#define PIMANN_ANN_HNSW_ADAPTER_H

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "ann/graph_view.h"

namespace pimann {

class TraceCollector;

/// Build-time parameters for the underlying hnswlib index.
struct HnswConfig {
  uint32_t dimension = 128;      ///< vector dimensionality
  uint32_t dtypeBytes = 4;       ///< bytes per component (float32 by default)
  uint32_t m = 16;               ///< max neighbours per node (hnswlib M)
  uint32_t efConstruction = 200; ///< build-time candidate list size
  uint32_t indexSeed = 100;
  uint32_t efSearch = 64; ///< query-time candidate list size
};

/// Thin wrapper over an hnswlib index. It owns the index, exposes its base-layer
/// topology as a @ref GraphView for the layout code, and runs *instrumented*
/// searches that feed a @ref TraceCollector.
///
/// Kept deliberately small: all heavy lifting stays in hnswlib. The adapter's
/// only jobs are (1) translate between our types and hnswlib's, and (2) expose
/// exactly the hooks the trace collector needs, so the instrumentation is
/// auditable and does not fabricate accesses.
class HnswAdapter : public GraphView {
public:
  explicit HnswAdapter(HnswConfig config);
  ~HnswAdapter() override;

  /// Add @p count vectors (row-major, @ref HnswConfig::dimension each) to the
  /// index, retaining corpus ids [0, count). An optional permutation controls
  /// insertion order without changing corpus IDs or the identity layout.
  void addVectors(const float *p_data, uint64_t count,
                  const std::vector<uint32_t> &insertionOrder = {});

  /// Run a single query with instrumentation. Every modelled memory access is
  /// forwarded to @p r_collector; the returned ids are the top-@p k results,
  /// best-first, for recall evaluation.
  std::vector<uint32_t> searchInstrumented(const float *p_query, uint32_t k,
                                           TraceCollector &r_collector) const;

  std::vector<uint32_t> searchStock(const float *query, uint32_t k) const;
  void setEf(uint32_t ef);
  uint32_t levelCount(uint64_t node) const override;
  const std::vector<uint32_t> &neighborsAt(uint64_t node, uint32_t level) const override;

  // --- GraphView ---------------------------------------------------------
  uint64_t nodeCount() const override;
  const std::vector<uint32_t> &neighbors(uint64_t nodeId) const override;
  uint32_t dimension() const override { return m_config.dimension; }
  uint32_t dtypeBytes() const override { return m_config.dtypeBytes; }

private:
  struct Impl; ///< hides the hnswlib headers from our translation units

  HnswConfig m_config;
  std::unique_ptr<Impl> m_impl;
};

} // namespace pimann

#endif // PIMANN_ANN_HNSW_ADAPTER_H
