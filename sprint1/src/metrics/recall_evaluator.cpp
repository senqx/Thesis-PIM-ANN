#include "metrics/recall_evaluator.h"

#include <algorithm>
#include <unordered_set>

namespace pimann {

void RecallEvaluator::addQuery(
    const std::vector<uint32_t>& groundTruth,
    const std::vector<uint32_t>& approxResult) {
  // Recall@k = |top-k(truth) intersect top-k(approx)| / k. We cap the truth set
  // at k and count how many returned ids fall inside it.
  const uint32_t topK = std::min<uint32_t>(m_k, groundTruth.size());
  if (topK == 0) {
    return;
  }
  std::unordered_set<uint32_t> truth(
      groundTruth.begin(), groundTruth.begin() + topK);

  const uint32_t limit = std::min<uint32_t>(m_k, approxResult.size());
  uint32_t hits = 0;
  for (uint32_t i = 0; i < limit; i++) {
    if (truth.count(approxResult[i]) != 0) {
      hits++;
    }
  }

  m_recallSum += static_cast<double>(hits) / topK;
  m_queryCount++;
}

double RecallEvaluator::recall() const {
  return m_queryCount == 0 ? 0.0 : m_recallSum / m_queryCount;
}

}  // namespace pimann
