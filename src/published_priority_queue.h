#pragma once
// Ordered-set implementation of the supplementary weighted queue's semantics.
// Equal-priority updates go to the front; untouched nodes retain initial order.
// The layout score updates and window-expiration rule remain in the source.
#include <cstdint>
#include <set>
#include <stdexcept>
#include <unordered_map>
#include <vector>

template <typename NodeId> class WeightedPriorityQueue {
  struct Entry {
    float priority;
    uint64_t serial;
    NodeId node;
  };
  struct Before {
    bool operator()(const Entry &a, const Entry &b) const {
      if (a.priority != b.priority)
        return a.priority > b.priority;
      if (a.serial != b.serial)
        return a.serial > b.serial;
      return a.node < b.node;
    }
  };
  using Queue = std::set<Entry, Before>;
  Queue queue;
  std::unordered_map<NodeId, typename Queue::iterator> locations;
  uint64_t serial = 0;
  void change(NodeId node, float delta) {
    auto found = locations.find(node);
    if (found == locations.end())
      return;
    float value = found->second->priority + delta;
    queue.erase(found->second);
    found->second = queue.insert({value, ++serial, node}).first;
  }

public:
  explicit WeightedPriorityQueue(size_t count) {
    for (size_t i = 0; i < count; ++i)
      locations.emplace(NodeId(i), queue.insert({0.0f, 0, NodeId(i)}).first);
  }
  void increment(NodeId node, float amount) { change(node, amount); }
  void decrement(NodeId node, float amount) { change(node, -amount); }
  NodeId pop() {
    if (queue.empty())
      throw std::runtime_error("empty published priority queue");
    auto first = queue.begin();
    NodeId node = first->node;
    locations.erase(node);
    queue.erase(first);
    return node;
  }
  size_t size() const { return queue.size(); }
};
