# pim-ann-demo — build the tools and run the experiments.
#
# IMPORTANT — two tiers of timing, never conflate them:
#   *-toy        -> analytical teaching model (toy_timing); illustrative ratios,
#                   NOT measured hardware. Fast, needs only a C++ compiler.
#   *-ramulator  -> cycle-accurate HBM2 via Ramulator 2.1 (scripts/). The
#                   trustworthy DRAM-locality numbers. Requires ./scripts/setup_ramulator.sh.
# The README's headline row-hit/cycle figures are the *-ramulator ones.
# Any "PIM speedup" printed by the toy model is an analytical estimate under
# assumed host/PIM bandwidths, not a measured PIM result.
CXX      ?= g++
CXXFLAGS ?= -std=c++20 -O2 -Wall
BIN      := bin
PYTHON   ?= python3

TOOLS := $(BIN)/ann_kernel $(BIN)/gen_trace $(BIN)/toy_timing $(BIN)/reorder $(BIN)/gen_layout

all: $(TOOLS)

$(BIN):
	mkdir -p $(BIN)

$(BIN)/%: src/%.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $< -o $@

# ===================================================================
# ANALYTICAL TOY MODEL (illustrative only — not measured hardware)
# ===================================================================

# Experiments 1-2 (toy): sequential (IVF/PQ) vs random (graph/HNSW).
.PHONY: demo-toy
demo-toy: all
	mkdir -p traces
	./$(BIN)/gen_trace --num_vectors 4096 --dim 128 --pattern seq  > traces/ann_seq.trace
	./$(BIN)/gen_trace --num_vectors 4096 --dim 128 --pattern rand > traces/ann_rand.trace
	@echo "## ANALYTICAL TOY MODEL (illustrative ratios, NOT measured HBM2)"
	./$(BIN)/toy_timing traces/ann_seq.trace
	@echo
	./$(BIN)/toy_timing traces/ann_rand.trace

# Experiment 3 (toy): size sweep (pattern vs dataset size).
.PHONY: sweep-toy
sweep-toy: all
	mkdir -p traces results
	@echo "pattern,num_vectors,host_cycles,pim_cycles,speedup_est,hit_rate" > results/sweep_toy.csv
	@for pat in seq rand; do \
	  for n in 1024 2048 4096 8192 16384 32768; do \
	    ./$(BIN)/gen_trace --num_vectors $$n --dim 128 --pattern $$pat > traces/t.trace 2>/dev/null; \
	    line=$$(./$(BIN)/toy_timing traces/t.trace --csv); \
	    echo "$$pat,$$n,$$(echo $$line|cut -d, -f2),$$(echo $$line|cut -d, -f3),$$(echo $$line|cut -d, -f4),$$(echo $$line|cut -d, -f5)" >> results/sweep_toy.csv; \
	  done; \
	done
	@echo "wrote results/sweep_toy.csv (analytical toy model)"; cat results/sweep_toy.csv

# Experiment 4 (toy): reorder the RANDOM trace within a window W.
.PHONY: optsweep-toy
optsweep-toy: all
	mkdir -p traces results
	./$(BIN)/gen_trace --num_vectors 4096 --dim 128 --pattern seq  > traces/opt_seq.trace
	./$(BIN)/gen_trace --num_vectors 4096 --dim 128 --pattern rand > traces/opt_rand.trace
	@echo "variant,window,host_cycles,pim_cycles,speedup_est,hit_rate" > results/optsweep_toy.csv
	@line=$$(./$(BIN)/toy_timing traces/opt_seq.trace --csv); \
	 echo "sequential,-,$$(echo $$line|cut -d, -f2),$$(echo $$line|cut -d, -f3),$$(echo $$line|cut -d, -f4),$$(echo $$line|cut -d, -f5)" >> results/optsweep_toy.csv
	@for W in 1 2 4 8 16 32 64 128 256; do \
	  ./$(BIN)/reorder $$W < traces/opt_rand.trace > traces/opt_w.trace; \
	  line=$$(./$(BIN)/toy_timing traces/opt_w.trace --csv); \
	  echo "random+reorder,$$W,$$(echo $$line|cut -d, -f2),$$(echo $$line|cut -d, -f3),$$(echo $$line|cut -d, -f4),$$(echo $$line|cut -d, -f5)" >> results/optsweep_toy.csv; \
	done
	@echo "wrote results/optsweep_toy.csv (analytical toy model)"; cat results/optsweep_toy.csv

# Experiment 5 (toy): cluster-ordered layout, sweep cluster size C.
.PHONY: layoutsweep-toy
layoutsweep-toy: all
	mkdir -p traces results
	@echo "cluster_C,host_cycles,pim_cycles,speedup_est,hit_rate" > results/layoutsweep_toy.csv
	@for C in 1 2 4 8 16 32 64 128 256; do \
	  ./$(BIN)/gen_layout --num_vectors 4096 --dim 128 --cluster $$C > traces/layout_c.trace 2>/dev/null; \
	  line=$$(./$(BIN)/toy_timing traces/layout_c.trace --csv); \
	  echo "$$C,$$(echo $$line|cut -d, -f2),$$(echo $$line|cut -d, -f3),$$(echo $$line|cut -d, -f4),$$(echo $$line|cut -d, -f5)" >> results/layoutsweep_toy.csv; \
	done
	@echo "wrote results/layoutsweep_toy.csv (analytical toy model)"; cat results/layoutsweep_toy.csv

# ===================================================================
# CYCLE-ACCURATE RAMULATOR HBM2 (the headline evidence)
# ===================================================================
# Reproduce the README numbers. Require ./scripts/setup_ramulator.sh first.

.PHONY: demo-ramulator
demo-ramulator: all
	mkdir -p traces
	./$(BIN)/gen_trace --num_vectors 4096 --dim 128 --pattern seq  > traces/ann_seq.trace
	./$(BIN)/gen_trace --num_vectors 4096 --dim 128 --pattern rand > traces/ann_rand.trace
	@echo "## CYCLE-ACCURATE HBM2 (Ramulator 2.1)"
	$(PYTHON) scripts/run_ann_ramulator.py traces/ann_seq.trace
	$(PYTHON) scripts/run_ann_ramulator.py traces/ann_rand.trace

.PHONY: layoutsweep-ramulator
layoutsweep-ramulator: all
	mkdir -p traces results
	@echo "cluster_C,cycles,row_hit_pct" > results/layoutsweep_ramulator.csv
	@for C in 1 4 16 32 64; do \
	  ./$(BIN)/gen_layout --num_vectors 4096 --dim 128 --cluster $$C > traces/layout_c.trace 2>/dev/null; \
	  $(PYTHON) scripts/run_ann_ramulator.py traces/layout_c.trace --csv >> results/layoutsweep_ramulator.csv; \
	done
	@echo "wrote results/layoutsweep_ramulator.csv (cycle-accurate HBM2)"; cat results/layoutsweep_ramulator.csv

# Backward-compatible aliases (default to the TOY model).
.PHONY: demo sweep optsweep layoutsweep
demo: demo-toy
sweep: sweep-toy
optsweep: optsweep-toy
layoutsweep: layoutsweep-toy

# Run the automated test suite (builds tools, checks validation + core claims).
.PHONY: test
test: all
	./tests/run_tests.sh

clean:
	rm -rf $(BIN) traces results
