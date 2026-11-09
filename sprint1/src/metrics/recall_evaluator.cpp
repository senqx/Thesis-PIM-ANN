#include "metrics/recall_evaluator.h"

#include <algorithm>
#include <unordered_set>

namespace pimann {

void RecallEvaluator::addQuery(const std::vector<uint32_t> &groundTruth,
                               const std::vector<uint32_t> &approxResult) {
  if (groundTruth.size() < m_k)
    throw std::invalid_argument("short recall ground truth");
  const uint32_t topK = m_k;
  std::unordered_set<uint32_t> truth(groundTruth.begin(), groundTruth.begin() + m_k);
  if (truth.size() != m_k)
    throw std::invalid_argument("duplicate ground truth ID");
  const uint32_t limit = std::min<uint32_t>(m_k, approxResult.size());
  std::unordered_set<uint32_t> seen;
  uint32_t hits = 0;
  for (uint32_t i = 0; i < limit; ++i) {
    if (!seen.insert(approxResult[i]).second)
      throw std::invalid_argument("duplicate result ID");
    hits += truth.count(approxResult[i]);
  }

  m_recallSum += static_cast<double>(hits) / topK;
  m_queryCount++;
}

double RecallEvaluator::recall() const {
  return m_queryCount == 0 ? 0.0 : m_recallSum / m_queryCount;
}

} // namespace pimann
