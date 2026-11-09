// Illustrative single-open-row teaching model with assumed bandwidths.
// Its ratios are not calibrated hardware measurements and are not thesis evidence.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>

struct Config {
  uint64_t t_rowhit = 4;     // cycles: data return when row already open
  uint64_t t_rowmiss = 24;   // cycles: close+open+return on a row conflict
  uint64_t row_bytes = 8192; // assumed teaching value
  uint64_t burst = 64;       // bytes per access
  double bw_host = 8.0;      // bytes/cycle across the off-chip bus (host)
  double bw_pim = 64.0;      // bytes/cycle on the near-bank internal path (PIM)
};

struct Result {
  uint64_t cycles = 0, hits = 0, misses = 0, bytes = 0;
};

static Result simulate(const std::string &path, const Config &c, bool pim) {
  std::ifstream in(path);
  if (!in) {
    std::fprintf(stderr, "cannot open %s\n", path.c_str());
    std::exit(1);
  }
  Result r;
  int64_t open_row = -1;
  const double bw = pim ? c.bw_pim : c.bw_host;
  std::string line, op, addr_s;
  while (std::getline(in, line)) {
    if (line.empty())
      continue;
    std::istringstream ss(line);
    ss >> op >> addr_s; // "LD 0x..." / "ST 0x..."
    uint64_t addr = std::strtoull(addr_s.c_str(), nullptr, 0);
    int64_t row = (int64_t)(addr / c.row_bytes);
    if (row == open_row) {
      r.cycles += c.t_rowhit;
      r.hits++;
    } else {
      r.cycles += c.t_rowmiss;
      r.misses++;
      open_row = row;
    }
    r.cycles += (uint64_t)(c.burst / bw);
    r.bytes += c.burst;
  }
  return r;
}

int main(int argc, char **argv) {
  if (argc < 2) {
    std::fprintf(stderr, "usage: %s <trace> [--csv]\n", argv[0]);
    return 1;
  }
  bool csv = (argc > 2 && std::string(argv[2]) == "--csv");
  Config c;
  Result h = simulate(argv[1], c, false), p = simulate(argv[1], c, true);
  const uint64_t accesses = h.hits + h.misses;
  if (accesses == 0) {
    std::fprintf(stderr,
                 "[toy_timing] error: trace '%s' has no LD/ST records (empty or malformed)\n",
                 argv[1]);
    return 1;
  }
  // accesses>0 guarantees nonzero cycles here, so these divisions are safe.
  double hr = 100.0 * h.hits / accesses;
  double speedup = p.cycles ? (double)h.cycles / p.cycles : 0.0;

  if (csv) {
    // trace,host_cycles,pim_cycles,speedup,hit_rate
    std::printf("%s,%llu,%llu,%.3f,%.1f\n", argv[1], (unsigned long long)h.cycles,
                (unsigned long long)p.cycles, speedup, hr);
    return 0;
  }
  auto row = [&](const char *n, const Result &r) {
    std::printf("  %-5s cycles=%-10llu hits=%llu misses=%llu hit-rate=%.1f%% achieved=%.1f B/cyc\n",
                n, (unsigned long long)r.cycles, (unsigned long long)r.hits,
                (unsigned long long)r.misses,
                (r.hits + r.misses) ? 100.0 * r.hits / (r.hits + r.misses) : 0.0,
                r.cycles ? (double)r.bytes / r.cycles : 0.0);
  };
  std::printf("=== %s ===\n", argv[1]);
  row("HOST", h);
  row("PIM", p);
  std::printf("  PIM speedup: %.2fx\n", speedup);
  return 0;
}
