CXX ?= g++
CXXFLAGS ?= -std=c++20 -O2 -Wall -Wextra
PYTHON ?= python3
TOOLS := bin/ann_kernel bin/gen_trace bin/toy_timing bin/reorder bin/gen_layout
.PHONY: all test test-simulator setup setup-published followup scheduling profiled-fetch demo-ramulator micro study sensitivity strengthen figures docs clean
all: $(TOOLS)
	$(MAKE) -C sprint1 all
bin:
	mkdir -p bin
bin/%: src/%.cpp src/trace_utils.h | bin
	$(CXX) $(CXXFLAGS) $< -o $@
test: all
	bash tests/run_tests.sh
	$(MAKE) -C sprint1 test
	$(PYTHON) tests/test_pipeline.py
	$(PYTHON) tests/test_experiments.py
	$(PYTHON) tests/test_followup.py
	$(PYTHON) tests/test_scheduling.py
	$(PYTHON) tests/test_profiled_fetch.py
	$(PYTHON) tests/test_reproduction.py
test-simulator:
	$(PYTHON) tests/test_simulator.py
setup:
	bash scripts/setup_ramulator.sh
setup-published:
	$(PYTHON) scripts/setup_published.py
followup: all
	$(PYTHON) scripts/followup.py --jobs 2
scheduling: all
	$(PYTHON) scripts/scheduling.py --jobs 2
profiled-fetch: all
	$(PYTHON) scripts/profiled_fetch.py --jobs 2
demo-ramulator: all
	mkdir -p work/demo
	bin/gen_trace --pattern seq --burst 32 > work/demo/seq.trace
	bin/gen_trace --pattern rand --burst 32 > work/demo/rand.trace
	$(PYTHON) scripts/run_ann_ramulator.py work/demo/seq.trace --output work/demo/seq.json
	$(PYTHON) scripts/run_ann_ramulator.py work/demo/rand.trace --output work/demo/rand.json
micro: all
	$(PYTHON) scripts/experiments.py micro
study: all
	$(PYTHON) scripts/experiments.py sift --seeds 10
sensitivity: all
	$(PYTHON) scripts/experiments.py sensitivity
strengthen: all
	$(PYTHON) scripts/strengthen.py all --jobs 2
figures:
	$(PYTHON) scripts/analyze.py
docs: figures
	bash scripts/build_docs.sh
clean:
	$(RM) -r bin
	$(MAKE) -C sprint1 clean
