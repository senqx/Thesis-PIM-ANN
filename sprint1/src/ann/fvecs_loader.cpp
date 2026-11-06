#include "ann/fvecs_loader.h"

#include <cstdint>
#include <fstream>
#include <stdexcept>

namespace pimann {

namespace {

/// Read a little-endian int32. Returns false at clean end of file.
bool readInt32(std::istream& r_in, int32_t& r_value) {
  return static_cast<bool>(
      r_in.read(reinterpret_cast<char*>(&r_value), sizeof(int32_t)));
}

}  // namespace

VecData loadFvecs(const std::string& path, uint64_t maxCount) {
  std::ifstream in(path, std::ios::binary);
  if (!in) {
    throw std::runtime_error("cannot open fvecs: " + path);
  }

  VecData out;
  int32_t dim = 0;
  while (readInt32(in, dim)) {
    if (dim <= 0) {
      throw std::runtime_error("invalid dimension in fvecs: " + path);
    }
    if (out.dim == 0) {
      out.dim = static_cast<uint32_t>(dim);
    } else if (static_cast<uint32_t>(dim) != out.dim) {
      throw std::runtime_error("ragged dimension in fvecs: " + path);
    }
    const size_t base = out.data.size();
    out.data.resize(base + out.dim);
    if (!in.read(
            reinterpret_cast<char*>(out.data.data() + base),
            static_cast<std::streamsize>(out.dim) * sizeof(float))) {
      throw std::runtime_error("truncated record in fvecs: " + path);
    }
    out.count++;
    if (maxCount != 0 && out.count >= maxCount) {
      break;
    }
  }
  return out;
}

std::vector<std::vector<uint32_t>> loadIvecs(
    const std::string& path, uint64_t maxCount) {
  std::ifstream in(path, std::ios::binary);
  if (!in) {
    throw std::runtime_error("cannot open ivecs: " + path);
  }

  std::vector<std::vector<uint32_t>> out;
  int32_t count = 0;
  while (readInt32(in, count)) {
    if (count < 0) {
      throw std::runtime_error("invalid count in ivecs: " + path);
    }
    std::vector<uint32_t> ids(static_cast<size_t>(count));
    if (count > 0 &&
        !in.read(
            reinterpret_cast<char*>(ids.data()),
            static_cast<std::streamsize>(count) * sizeof(int32_t))) {
      throw std::runtime_error("truncated record in ivecs: " + path);
    }
    out.push_back(std::move(ids));
    if (maxCount != 0 && out.size() >= maxCount) {
      break;
    }
  }
  return out;
}

}  // namespace pimann
