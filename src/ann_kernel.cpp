// Educational squared-L2 scan over signed-byte vectors. This is neither PQ
// nor graph traversal; its visitation order does not change the top-k problem.
#include "trace_utils.h"
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <random>
#include <string>
#include <vector>

struct Args {
  uint64_t num_vectors = 4096; // candidates in this scan
  uint64_t dim = 128;          // vector dimensionality (128 ~ SIFT)
  std::string pattern = "seq"; // "seq" or "rand"
  uint64_t topk = 10;
  uint64_t seed = 1;
};

[[noreturn]] static void die(const std::string &msg) {
  fprintf(stderr, "[ann_kernel] error: %s\n", msg.c_str());
  std::exit(1);
}

static Args parse(int argc, char **argv) {
  Args a;
  for (int i = 1; i < argc; i++) {
    std::string k = argv[i];
    auto v = [&](const char *flag) -> std::string {
      if (i + 1 >= argc)
        die(std::string("missing value for ") + flag);
      return std::string(argv[++i]);
    };
    if (k == "--num_vectors")
      a.num_vectors = integer(v("--num_vectors"));
    else if (k == "--dim")
      a.dim = integer(v("--dim"));
    else if (k == "--pattern")
      a.pattern = v("--pattern");
    else if (k == "--topk")
      a.topk = integer(v("--topk"));
    else if (k == "--seed")
      a.seed = integer(v("--seed"));
    else
      die("unknown argument: " + k);
  }
  // Input validation.
  if (a.num_vectors == 0)
    die("--num_vectors must be > 0");
  if (a.dim == 0)
    die("--dim must be > 0");
  if (a.topk == 0)
    die("--topk must be > 0");
  if (a.pattern != "seq" && a.pattern != "rand")
    die("--pattern must be 'seq' or 'rand' (got '" + a.pattern + "')");
  if (a.topk > a.num_vectors)
    die("topk exceeds corpus size");
  if (a.dim > INT32_MAX / (255 * 255))
    die("dimension exceeds int32 distance range");
  if (a.dim > (SIZE_MAX / a.num_vectors))
    die("num_vectors * dim overflows allocation size");
  return a;
}

int main(int argc, char **argv) try {
  Args a = parse(argc, argv);

  // --- set up synthetic signed-byte vectors ---
  std::mt19937 rng(a.seed);
  std::uniform_int_distribution<int> d(-128, 127);
  std::vector<int8_t> data(a.num_vectors * a.dim);
  for (auto &x : data)
    x = (int8_t)d(rng);
  std::vector<int8_t> query(a.dim);
  for (auto &x : query)
    x = (int8_t)d(rng);

  // visitation order: sequential or shuffled (graph-traversal mimic)
  std::vector<uint64_t> order(a.num_vectors);
  for (uint64_t i = 0; i < a.num_vectors; i++)
    order[i] = i;
  if (a.pattern == "rand")
    std::shuffle(order.begin(), order.end(), rng);

  // --- the memory-bound inner loop: distance to every candidate ---
  using Pair = std::pair<int64_t, uint64_t>; // (distance, id)
  std::vector<Pair> best;
  best.reserve(a.topk + 1);
  for (uint64_t idx = 0; idx < a.num_vectors; idx++) {
    uint64_t v = order[idx];
    const int8_t *cand = &data[v * a.dim];
    int64_t dist = 0;
    for (uint64_t j = 0; j < a.dim; j++) { // squared L2 distance
      int64_t diff = (int64_t)query[j] - (int64_t)cand[j];
      dist += diff * diff;
    }
    // maintain top-k (small k -> cheap)
    if (best.size() < a.topk) {
      best.push_back({dist, v});
      std::push_heap(best.begin(), best.end());
    } else if (dist < best.front().first) {
      std::pop_heap(best.begin(), best.end());
      best.back() = {dist, v};
      std::push_heap(best.begin(), best.end());
    }
  }
  std::sort_heap(best.begin(), best.end());

  printf("ANN kernel: %llu vectors, dim=%llu, pattern=%s, top-%llu\n",
         (unsigned long long)a.num_vectors, (unsigned long long)a.dim, a.pattern.c_str(),
         (unsigned long long)a.topk);
  printf("nearest ids (dist): ");
  for (auto &p : best)
    printf("%llu(%lld) ", (unsigned long long)p.second, (long long)p.first);
  printf("\n");
  return 0;
}

catch (const std::exception &e) {
  std::fprintf(stderr, "ann_kernel: %s\n", e.what());
  return 1;
}
