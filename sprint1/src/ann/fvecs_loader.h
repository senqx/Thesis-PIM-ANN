#ifndef PIMANN_ANN_FVECS_LOADER_H
#define PIMANN_ANN_FVECS_LOADER_H

#include <cstdint>
#include <string>
#include <vector>

namespace pimann {

/// Vectors loaded from a .fvecs / .ivecs file, flattened row-major.
struct VecData {
  std::vector<float> data;  ///< count * dim, row-major
  uint32_t dim = 0;
  uint64_t count = 0;
};

/// Load a TEXMEX .fvecs file (SIFT1M/GIST1M format): each record is an int32
/// dimension followed by @p dim float32 components. Throws on I/O or format
/// error. @p maxCount caps how many vectors are read (0 = all), useful for
/// quick runs on a subset.
VecData loadFvecs(const std::string& path, uint64_t maxCount = 0);

/// Load a .ivecs file (ground-truth neighbour ids): each record is an int32
/// count followed by that many int32 ids. Returns one id list per query.
std::vector<std::vector<uint32_t>> loadIvecs(
    const std::string& path, uint64_t maxCount = 0);

}  // namespace pimann

#endif  // PIMANN_ANN_FVECS_LOADER_H
