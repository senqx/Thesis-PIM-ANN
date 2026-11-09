// Address sort within disjoint batches of read-only burst records.
// Does not model whether a graph search can expose those requests concurrently.
#include "trace_utils.h"
#include <algorithm>
#include <iostream>
#include <sstream>
#include <vector>
int main(int argc, char **argv) try {
  if (argc != 2)
    throw std::invalid_argument("usage: reorder <window> < input > output");
  const auto window = integer(argv[1]);
  if (!window)
    throw std::invalid_argument("zero window");
  struct Record {
    uint64_t address;
    std::string line;
  };
  std::vector<Record> records;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream row(line);
    std::string op, address, extra;
    if (!(row >> op >> address) || op != "LD" || row >> extra)
      throw std::invalid_argument("expected LD address; stores/query streams cannot be reordered");
    records.push_back({integer(address), line});
  }
  if (!std::cin.eof() || records.empty())
    throw std::invalid_argument("empty or unreadable input");
  for (size_t i = 0; i < records.size();) {
    size_t end = i + std::min<uint64_t>(window, records.size() - i);
    std::stable_sort(records.begin() + i, records.begin() + end,
                     [](const auto &a, const auto &b) { return a.address < b.address; });
    i = end;
  }
  for (const auto &r : records)
    std::cout << r.line << '\n';
  if (!std::cout)
    throw std::runtime_error("output failed");
} catch (const std::exception &e) {
  std::cerr << "reorder: " << e.what() << '\n';
  return 1;
}
