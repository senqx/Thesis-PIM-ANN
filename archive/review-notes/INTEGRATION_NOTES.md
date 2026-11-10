# Integration boundary

The current pipeline integrates stock HNSW demand tracing, explicit separate-array
storage, five bijective vector mappings, native HBM2 request emission, and a draining
bounded frontend. The maintained commands are in the root README.

A future physical ANN/PIM implementation would additionally need dependency-aware
query execution, mapping lookup traffic, local storage/cache modelling, compute and
host-transfer costs, and genuinely quantised distances if using a compact index.
Those are outside the current thesis's bounded DRAM-locality questions. They are
not silently included in its reported cycle counts.
