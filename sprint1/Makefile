# Sprint-1: real-HNSW trace pipeline + graph-aware layouts.
# Builds with just a C++20 compiler; hnswlib is vendored under third_party/.

CXX      ?= g++
CXXFLAGS ?= -std=c++20 -O2 -Wall -Wextra
INCLUDES := -I src -I third_party

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

.PHONY: all clean bench sift synth figures

all: run_bench run_synth run_sift

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

# Convenience: run the synthetic benchmark and regenerate figures.
bench: run_bench
	./run_bench 8000 300 150 | tee bench_human.txt

# Synthetic run that emits the 4 layout traces for Ramulator replay.
synth: run_synth
	./run_synth 20000 400 200 64

figures: bench.csv
	python3 make_figs.py

# Run on real SIFT1M. Expects data/sift_base.fvecs + data/sift_query.fvecs
# (download: ftp://ftp.irisa.fr/local/texmex/corpus/sift.tar.gz).
# Override subset size with MAXBASE=...
MAXBASE ?= 100000
sift: run_sift
	./run_sift data/sift_base.fvecs data/sift_query.fvecs $(MAXBASE) 500 200 64

clean:
	rm -f run_bench run_sift *.ldst *.png bench_human.txt
