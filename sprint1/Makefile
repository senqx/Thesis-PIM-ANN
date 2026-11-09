CXX ?= g++
CXXFLAGS ?= -std=c++20 -O2 -Wall -Wextra
CPPFLAGS := -I src -isystem third_party -DHNSWLIB_USE_PREFETCH=0
CORE := $(wildcard src/ann/*.cpp src/layout/*.cpp src/memory/*.cpp src/metrics/*.cpp) src/layout_metrics.cpp
OBJECTS := $(patsubst src/%.cpp,build/%.o,$(CORE))
.PHONY: all test bench clean
all: run_study
build/%.o: src/%.cpp
	mkdir -p $(@D)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -MMD -MP -c $< -o $@
run_study: build/run_study.o $(OBJECTS)
	$(CXX) $(CXXFLAGS) $^ -o $@
build/test_core: tests/test_core.cpp $(OBJECTS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $^ -o $@
test: all build/test_core
	./build/test_core
bench: all
	./run_study --output ../work/synthetic
clean:
	$(RM) -r build run_study
-include $(OBJECTS:.o=.d) build/run_study.d
