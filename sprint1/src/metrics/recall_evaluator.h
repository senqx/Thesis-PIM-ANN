#ifndef PIMANN_METRICS_RECALL_EVALUATOR_H
#define PIMANN_METRICS_RECALL_EVALUATOR_H

#include <cstdint>
#include <vector>

namespace pimann {

/// Accumulates Recall@k over a query set. Recall@k is the fraction of each
/// query's true k nearest neighbours that the approximate search actually
/// returned, averaged over queries. It is the guard-rail metric for the whole
/// thesis: any layout change must leave it essentially unmoved (target: at most
/// one point of Recall@10 loss versus baseline).
class RecallEvaluator {
public:
  /// @p k is the neighbourhood size recall is measured at (e.g. 10).
  explicit RecallEvaluator(uint32_t k) : m_k(k) {}

  /// Record one query. @p groundTruth holds the exact nearest-neighbour ids
  /// (at least @ref m_k of them); @p approxResult holds the ids the search
  /// returned, best-first. Only the top-k of each are compared.
  void addQuery(
      const std::vector<uint32_t>& groundTruth,
      const std::vector<uint32_t>& approxResult);

  /// Mean Recall@k across all recorded queries, in [0, 1].
  double recall() const;

  /// Number of queries recorded.
  uint64_t queryCount() const { return m_queryCount; }

private:
  uint32_t m_k;
  double m_recallSum = 0.0;
  uint64_t m_queryCount = 0;
};

}  // namespace pimann

#endif  // PIMANN_METRICS_RECALL_EVALUATOR_H
