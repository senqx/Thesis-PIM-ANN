#pragma once
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <stdexcept>
#include <string>
inline uint64_t integer(const std::string &s) {
  if (s.empty() || s[0] == '-' || s[0] == '+')
    throw std::invalid_argument("invalid unsigned integer: " + s);
  char *end = nullptr;
  errno = 0;
  auto n = std::strtoull(s.c_str(), &end, 0);
  if (errno == ERANGE || end == s.c_str() || *end)
    throw std::invalid_argument("invalid unsigned integer: " + s);
  return n;
}
inline uint64_t emit_payload(uint64_t addr, uint64_t bytes, uint64_t burst) {
  uint64_t count = 0, end = addr + bytes;
  for (uint64_t a = addr - addr % burst; a < end;) {
    if (std::printf("LD 0x%llx\n", (unsigned long long)a) < 0)
      throw std::runtime_error("trace output failed");
    ++count;
    if (a > UINT64_MAX - burst)
      break;
    a += burst;
  }
  return count;
}
