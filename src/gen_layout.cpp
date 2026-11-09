// Controlled read-only contiguous-run microbenchmark; no graph traversal is implied.
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
  fprintf(stderr, "[gen_layout] error: %s\n", msg.c_str());
  std::exit(1);
}

} // namespace

int main(int argc, char **argv) try {
  uint64_t num_vectors = 4096, dim = 128, dtype_bytes = 1, base = 0x100000, seed = 1;
  uint64_t quality = 100;
  uint64_t cluster = 16, burst = 64; // cluster = vectors co-located per block

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
    else if (k == "--cluster")
      cluster = nn("--cluster");
    else if (k == "--base")
      base = nn("--base");
    else if (k == "--quality")
      quality = nn("--quality");
    else if (k == "--burst")
      burst = nn("--burst");
    else if (k == "--seed")
      seed = nn("--seed");
    else
      die("unknown argument: " + k);
  }

  if (!burst || (burst & (burst - 1)))
    die("burst must be a power of two");
  // Input validation.
  if (num_vectors == 0)
    die("--num_vectors must be > 0");
  if (dim == 0)
    die("--dim must be > 0");
  if (dtype_bytes == 0)
    die("--dtype must be > 0");
  if (cluster == 0)
    die("--cluster must be > 0");
  if (dim > UINT64_MAX / dtype_bytes)
    die("dim * dtype overflows");
  const uint64_t vec_bytes = dim * dtype_bytes;
  if (num_vectors > (UINT64_MAX - base) / vec_bytes)
    die("num_vectors * vec_bytes overflows the address space");

  // cluster ids in random visitation order; vectors within a cluster contiguous
  const uint64_t n_clusters = 1 + (num_vectors - 1) / cluster;
  std::vector<uint64_t> cl(n_clusters);
  std::iota(cl.begin(), cl.end(), 0ULL);
  std::mt19937 rng(seed);
  std::shuffle(cl.begin(), cl.end(), rng);

  if (quality > 100)
    die("quality outside 0..100");
  std::vector<uint64_t> slots(num_vectors), selected(num_vectors);
  std::iota(slots.begin(), slots.end(), 0);
  std::iota(selected.begin(), selected.end(), 0);
  std::mt19937 placement(seed + 101);
  std::shuffle(selected.begin(), selected.end(), placement);
  const uint64_t displaced =
      num_vectors - (num_vectors / 100 * quality + (num_vectors % 100) * quality / 100);
  if (displaced == 1)
    die("one displaced slot cannot form a permutation");
  // A cycle deranges precisely the selected slots, preserving the address multiset.
  for (uint64_t i = 0; i < displaced; ++i)
    slots[selected[i]] = selected[(i + 1) % displaced];
  uint64_t loads = 0, bytes = 0;
  for (uint64_t c : cl) {
    for (uint64_t j = 0; j < cluster; j++) {
      uint64_t v = c * cluster + j;
      if (v >= num_vectors)
        break;
      uint64_t addr = base + slots[v] * vec_bytes; // contiguous placement
      loads += emit_payload(addr, vec_bytes, burst);
    }
  }
  bytes = loads * burst;
  if (std::fflush(stdout))
    die("trace output failed");
  fprintf(stderr, "[gen_layout] vectors=%llu dim=%llu cluster=%llu  -> %llu LD records (%.2f MB)\n",
          (unsigned long long)num_vectors, (unsigned long long)dim, (unsigned long long)cluster,
          (unsigned long long)loads, bytes / (1024.0 * 1024.0));
  return 0;
}

catch (const std::exception &e) {
  std::fprintf(stderr, "%s\n", e.what());
  return 1;
}
