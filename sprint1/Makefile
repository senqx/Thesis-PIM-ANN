# Sprint-1: real-HNSW trace pipeline + graph-aware layouts.
# Builds with just a C++20 compiler; hnswlib is vendored under third_party/.

CXX      ?= g++
CXXFLAGS ?= -std=c++20 -O2 -Wall -Wextra
# -isystem (not -I) for third_party: silences warnings from vendored hnswlib
# while keeping full -Wall -Wextra on our own code. Our code builds warning-free.
INCLUDES := -I src -isystem third_party

CORE := \
  src/ann/hnsw_adapter.cpp \
  src/ann/trace_collector.cpp \
  src/ann/fvecs_loader.cpp \
  src/layout/random_layout.cpp \
  src/layout/bfs_layout.cpp \
  src/layout/community_layout.cpp \
  src/layout/covisitation_model.cpp \
  src/layout/query_aware_layout.cpp \
  src/layout_metrics.cpp \
  src/memory/address_emitter.cpp \
  src/metrics/recall_evaluator.cpp

.PHONY: all clean bench sift synth dtype figures

all: run_bench run_synth run_sift run_dtype

# Synthetic benchmark (no dataset needed): 4 layouts + efSearch sweep.
run_bench: src/run_bench.cpp $(CORE)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $^ -o $@

# Synthetic driver that EMITS the 4 layout traces (no dataset needed), so you
# can get cycle-accurate Ramulator numbers without downloading SIFT1M.
run_synth: src/run_synth.cpp $(CORE)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $^ -o $@

# Real-dataset driver: pass SIFT1M .fvecs paths (see `make sift`).
run_sift: src/run_sift.cpp $(CORE)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $^ -o $@

# Byte-budget sweep: float32 vs int8 vectors-per-row. Pass .fvecs paths for the
# real test (recommended