// Adapter for Coleman et al.'s NeurIPS 2022 layout routines.
// The weighted queue helper is replaced with equivalent ordered-set operations.
// The pinned supplementary headers are fetched by scripts/setup_published.py.
#include "reordering.h"
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

int main(int argc, char **argv) try {
  if (argc != 5)
    throw std::invalid_argument("published_layouts graph.csv profile.csv method output.csv");
  std::ifstream graphFile(argv[1]), profileFile(argv[2]);
  if (!graphFile || !profileFile)
    throw std::runtime_error("missing graph or training profile");
  std::vector<std::vector<uint32_t>> graph;
  std::string line;
  std::getline(graphFile, line);
  if (line != "node,level,neighbors")
    throw std::runtime_error("invalid graph header");
  while (std::getline(graphFile, line)) {
    std::istringstream row(line);
    std::string a, b;
    std::getline(row, a, ',');
    std::getline(row, b, ',');
    auto node = std::stoul(a), level = std::stoul(b);
    if (level)
      continue;
    if (node != graph.size())
      throw std::runtime_error("non-dense graph IDs");
    graph.emplace_back();
    std::unordered_set<uint32_t> seen;
    uint32_t v;
    while (row >> v) {
      if (v == node || !seen.insert(v).second)
        throw std::runtime_error("self/duplicate edge");
      graph.back().push_back(v);
    }
  }
  if (graph.empty())
    throw std::runtime_error("empty graph");
  for (const auto &neighbors : graph)
    for (auto v : neighbors)
      if (v >= graph.size())
        throw std::runtime_error("edge outside graph");
  std::vector<std::vector<float>> weights;
  for (const auto &neighbors : graph)
    weights.emplace_back(neighbors.size(), 1.0f);
  std::getline(profileFile, line);
  if (line != "source,target,traversals")
    throw std::runtime_error("invalid profile header");
  while (std::getline(profileFile, line)) {
    std::replace(line.begin(), line.end(), ',', ' ');
    std::istringstream row(line);
    uint32_t source, target, count;
    if (!(row >> source >> target >> count) || source >= graph.size() || !count)
      throw std::runtime_error("invalid profile record");
    const auto &neighbors = graph[source];
    auto it = std::find(neighbors.begin(), neighbors.end(), target);
    if (it == neighbors.end())
      throw std::runtime_error("profile contains non-edge");
    weights[source][it - neighbors.begin()] += count;
  }
  auto start = std::chrono::steady_clock::now();
  std::vector<uint32_t> mapping;
  const std::string method(argv[3]);
  if (method == "rcm")
    mapping = rcm_order<uint32_t>(graph);
  else if (method == "gorder")
    mapping = g_order<uint32_t>(graph, 5);
  else if (method == "porder")
    mapping = weighted_g_order<uint32_t>(graph, weights, 5);
  else
    throw std::invalid_argument("unknown published method");
  double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
  std::vector<bool> seen(graph.size(), false);
  if (mapping.size() != graph.size())
    throw std::runtime_error("short permutation");
  for (auto slot : mapping) {
    if (slot >= graph.size() || seen[slot])
      throw std::runtime_error("invalid permutation");
    seen[slot] = true;
  }
  std::ofstream out(argv[4]);
  out.exceptions(std::ios::failbit | std::ios::badbit);
  out << "logicalId,slot\n";
  for (size_t node = 0; node < mapping.size(); ++node)
    out << node << ',' << mapping[node] << '\n';
  out.close();
  std::cout << "{\"layout_seconds\":" << elapsed << ",\"nodes\":" << graph.size() << "}\n";
} catch (const std::exception &e) {
  std::cerr << e.what() << '\n';
  return 1;
}
