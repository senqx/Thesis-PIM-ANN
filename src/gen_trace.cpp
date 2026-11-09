// Controlled read-only sequential/permuted vector-read microbenchmark.
#include "trace_utils.h"
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <numeric>
#include <random>
#include <string>
#include <vector>

namespace {

[[noreturn]] void die(const std::string &msg) {
  fprintf(stderr, "[gen_trace] error: %s\n", msg.c_str());
  std::exit(1);
}

} // namespace

int main(int argc, char **argv) try {
  uint64_t num_vectors = 4096, dim = 128, dtype_bytes = 1, base = 0x100000, seed = 1;
  uint64_t burst = 64; // DRAM access granularity (cache line)
  std::string pattern = "seq";

  for (int i = 1; i < argc; i++) {
    std::string k = argv[i];
    auto next = [&](const char *flag) -> const char * {
      if (i + 1 >= argc)
        die(std::string("missing value for ") + flag);
      return argv[++i];
    };
    auto nn = [&](const char *flag) { return integer(next(flag)); };
    if (k == "--num_vectors")
      num_vectors = nn("--num_vectors");
    else if (k == "--dim")
      dim = nn("--dim");
    else if (k == "--dtype")
      dtype_bytes = nn("--dtype");
    else if (k == "--base")
      base = nn("--base");
    else if (k == "--burst")
      burst = nn("--burst");
    else if (k == "--seed")
      seed = nn("--seed");
    else if (k == "--pattern")
      pattern = next("--pattern");
    else
      die("unknown argument: " + k);
  }

  if (!burst || (burst & (burst - 1)))
    die("burst must be a power of two");
  // Input validation (reject values that would silently produce garbage).
  if (num_vectors == 0)
    die("--num_vectors must be > 0");
  if (dim == 0)
    die("--dim must be > 0");
  if (dtype_bytes == 0)
    die("--dtype must be > 0");
  if (pattern != "seq" && pattern != "rand")
    die("--pattern must be 'seq' or 'rand' (got '" + pattern + "')");
  // Guard the multiplications against overflow (would wrap the address space).
  if (dim > UINT64_MAX / dtype_bytes)
    die("dim * dtype overflows");
  const uint64_t vec_bytes = dim * dtype_bytes;
  if (num_vectors > (UINT64_MAX - base) / vec_bytes)
    die("num_vectors * vec_bytes overflows the address space");

  std::vector<uint64_t> order(num_vectors);
  std::iota(order.begin(), order.end(), 0ULL);
  if (pattern == "rand") {
    std::mt19937 rng(seed);
    std::shuffle(order.begin(), order.end(), rng);
  }

  uint64_t loads = 0, bytes = 0;
  for (uint64_t v : order) {
    uint64_t addr = base + v * vec_bytes;
    loads += emit_payload(addr, vec_bytes, burst);
  }

  bytes = loads * burst;
  if (std::fflush(stdout))
    die("trace output failed");
  fprintf(stderr,
          "[gen_trace] pattern=%s vectors=%llu dim=%llu dtype=%lluB vec_bytes=%llu\n"
          "[gen_trace] emitted %llu LD records (%lluB bursts) = %.2f MB\n",
          pattern.c_str(), (unsigned long long)num_vectors, (unsigned long long)dim,
          (unsigned long long)dtype_bytes, (unsigned long long)vec_bytes, (unsigned long long)loads,
          (unsigned long long)burst, bytes / (1024.0 * 1024.0));
  return 0;
}

catch (const std::exception &e) {
  std::fprintf(stderr, "%s\n", e.what());
  return 1;
}
