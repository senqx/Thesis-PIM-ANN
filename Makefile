# pim-ann-demo — build the tools and run the experiments
CXX      ?= g++
CXXFLAGS ?= -std=c++20 -O2 -Wall
BIN      := bin

TOOLS := $(BIN)/ann_kernel $(BIN)/gen_trace $(BIN)/toy_timing $(BIN)/reorder $(BIN)/gen_layout

all: $(TOOLS)

$(BIN):
	mkdir -p $(BIN)

$(BIN)/%: src/%.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $< -o $@

# Experiments 1-2: sequential (IVF/PQ) vs random (graph/HNSW).
.PHONY: demo
demo: all
	mkdir -p traces
	./$(BIN)/gen_trace --num_vectors 4096 --dim 128 --pattern seq  > traces/ann_seq.trace
	./$(BIN)/gen_trace --num_vectors 4096 --dim 128 --pattern rand > traces/ann_rand.trace
	@echo
	./$(BIN)/toy_timing traces/ann_seq.trace
	@echo
	./$(BIN)/toy_timing traces/ann_rand.trace

# Experiment 3: size sweep (pattern vs dataset size).
.PHONY: sweep
sweep: all
	mkdir -p traces results
	@echo "pattern,num_vectors,host_cycles,pim_cycles,speedup,hit_rate" > results/sweep.csv
	@for pat in seq rand; do \
	  for n in 1024 2048 4096 8192 16384 32768; do \
	    ./$(BIN)/gen_trace --num_vectors $$n --dim 128 --pattern $$pat > traces/t.trace 2>/dev/null; \
	    line=$$(./$(BIN)/toy_timing traces/t.trace --csv); \
	    echo "$$pat,$$n,$$(echo $$line|cut -d, -f2),$$(echo $$line|cut -d, -f3),$$(echo $$line|cut -d, -f4),$$(echo $$line|cut -d, -f5)" >> results/sweep.csv; \
	  done; \
	done
	@echo "wrote results/sweep.csv"; cat results/sweep.csv

# Experiment 4 (locality recovery): reorder the RANDOM trace within a window W
# and watch the row-hit rate / PIM speedup climb back toward sequential.
# Models query batching / a deeper controller reorder window.
.PHONY: optsweep
optsweep: all
	mkdir -p traces results
	./$(BIN)/gen_trace --num_vectors 4096 --dim 128 --pattern seq  > traces/opt_seq.trace
	./$(BIN)/gen_trace --num_vectors 4096 --dim 128 --pattern rand > traces/opt_rand.trace
	@echo "variant,window,host_cycles,pim_cycles,speedup,hit_rate" > results/optsweep.csv
	@line=$$(./$(BIN)/toy_timing traces/opt_seq.trace --csv); \
	 echo "sequential,-,$$(echo $$line|cut -d, -f2),$$(echo $$line|cut -d, -f3),$$(echo $$line|cut -d, -f4),$$(echo $$line|cut -d, -f5)" >> results/optsweep.csv
	@for W in 1 2 4 8 16 32 64 128 256; do \
	  ./$(BIN)/reorder $$W < traces/opt_rand.trace > traces/opt_w.trace; \
	  line=$$(./$(BIN)/toy_timing traces/opt_w.trace --csv); \
	  echo "random+reorder,$$W,$$(echo $$line|cut -d, -f2),$$(echo $$line|cut -d, -f3),$$(echo $$line|cut -d, -f4),$$(echo $$line|cut -d, -f5)" >> results/optsweep.csv; \
	done
	@echo "wrote results/optsweep.csv"; cat results/optsweep.csv

# Experiment 5 (THE FIX): cluster-ordered layout. Visit clusters in random order
# but co-locate vectors within a cluster; sweep cluster size C and watch row-hit
# recover toward the sequential ceiling. On real HBM2 it saturates by C ~ 16.
.PHONY: layoutsweep
layoutsweep: all
	mkdir -p traces results
	@echo "cluster_C,host_cycles,pim_cycles,speedup,hit_rate" > results/layoutsweep.csv
	@for C in 1 2 4 8 16 32 64 128 256; do \
	  ./$(BIN)/gen_layout --num_vectors 4096 --dim 128 --cluster $$C > traces/layout_c.trace 2>/dev/null; \
	  line=$$(./$(BIN)/toy_timing traces/layout_c.trace --csv); \
	  echo "$$C,$$(echo $$line|cut -d, -f2),$$(echo $$line|cut -d, -f3),$$(echo $$line|cut -d, -f4),$$(echo $$line|cut -d, -f5)" >> results/layoutsweep.csv; \
	done
	@echo "wrote results/layoutsweep.csv"; cat results/layoutsweep.csv

clean:
	rm -rf $(BIN) traces results
