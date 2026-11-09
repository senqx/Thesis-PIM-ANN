#ifndef PIMANN_METRICS_RECALL_EVALUATOR_H
#define PIMANN_METRICS_RECALL_EVALUATOR_H

#include <cstdint>
#include <stdexcept>
#include <vector>

namespace pimann {

/// Mean ID-based Recall@k; callers supply exact ground truth for their corpus.
class RecallEvaluator {
public:
  /// @p k is the neighbourhood size recall is measured at (e.g. 10).
  explicit RecallEvaluator(uint32_t k) : m_k(k) {
    if (!k)
      throw std::invalid_argument("zero recall k");
  }

  /// Record one query. @p groundTruth holds the exact nearest-neighbour ids
  /// (at least @ref m_k of them); @p approxResult holds the ids the search
  /// returned, best-first. Only the top-k of each are compared.
  void addQuery(const std::vector<uint32_t> &groundTruth,
                const std::vector<uint32_t> &approxResult);

  /// Mean Recall@k across all recorded queries, in [0, 1].
  double recall() const;

  /// Number of queries recorded.
  uint64_t queryCount() const { return m_queryCount; }

private:
  uint32_t m_k;
  double m_recallSum = 0.0;
  uint64_t m_queryCount = 0;
};

} // namespace pimann

#endif // PIMANN_METRICS_RECALL_EVALUATOR_H
