#include "ann/fvecs_loader.h"

#include <bit>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <limits>
#include <stdexcept>

namespace pimann {

namespace {

/// Read a little-endian int32. Returns false at clean end of file.
bool readInt32(std::istream &r_in, int32_t &r_value) {
  static_assert(std::endian::native == std::endian::little, "fvecs requires little endian");
  r_in.read(reinterpret_cast<char *>(&r_value), sizeof(int32_t));
  if (r_in.gcount() == 0 && r_in.eof())
    return false;
  if (r_in.gcount() != sizeof(int32_t))
    throw std::runtime_error("truncated dimension header");
  return true;
}

} // namespace

VecData loadFvecs(const std::string &path, uint64_t maxCount) {
  std::ifstream in(path, std::ios::binary);
  if (!in) {
    throw std::runtime_error("cannot open fvecs: " + path);
  }

  VecData out;
  int32_t dim = 0;
  while (readInt32(in, dim)) {
    if (dim <= 0 || dim > 65536) {
      throw std::runtime_error("invalid dimension in fvecs: " + path);
    }
    if (out.dim == 0) {
      out.dim = static_cast<uint32_t>(dim);
    } else if (static_cast<uint32_t>(dim) != out.dim) {
      throw std::runtime_error("ragged dimension in fvecs: " + path);
    }
    const size_t base = out.data.size();
    out.data.resize(base + out.dim);
    if (!in.read(reinterpret_cast<char *>(out.data.data() + base),
                 static_cast<std::streamsize>(out.dim) * sizeof(float))) {
      throw std::runtime_error("truncated record in fvecs: " + path);
    }
    for (size_t i = base; i < out.data.size(); ++i)
      if (!std::isfinite(out.data[i]))
        throw std::runtime_error("nonfinite fvecs component");
    out.count++;
    if (maxCount != 0 && out.count >= maxCount) {
      break;
    }
  }
  if (out.data.empty())
    throw std::runtime_error("empty fvecs: " + path);
  return out;
}

std::vector<std::vector<uint32_t>> loadIvecs(const std::string &path, uint64_t maxCount) {
  std::ifstream in(path, std::ios::binary);
  if (!in) {
    throw std::runtime_error("cannot open ivecs: " + path);
  }

  std::vector<std::vector<uint32_t>> out;
  int32_t count = 0;
  while (readInt32(in, count)) {
    if (count <= 0 || count > 1000000) {
      throw std::runtime_error("invalid count in ivecs: " + path);
    }
    std::vector<uint32_t> ids(static_cast<size_t>(count));
    if (count > 0 && !in.read(reinterpret_cast<char *>(ids.data()),
                              static_cast<std::streamsize>(count) * sizeof(int32_t))) {
      throw std::runtime_error("truncated record in ivecs: " + path);
    }
    for (auto id : ids)
      if (id > INT32_MAX)
        throw std::runtime_error("negative ivecs ID");
    out.push_back(std::move(ids));
    if (maxCount != 0 && out.size() >= maxCount) {
      break;
    }
  }
  if (out.empty())
    throw std::runtime_error("empty ivecs: " + path);
  return out;
}

} // namespace pimann
