# Vendored HNSW source

The source present at thesis commit `40d0edd` is retained. That commit did not
record a verifiable upstream revision, so this artifact identifies the exact
vendored files with SHA-256 hashes in `provenance.json` rather than inventing a
release tag. Upstream hnswlib is licensed under Apache 2.0; the license is included
as `LICENSE.hnswlib`.

The current patch to `hnswalg.h` adds `<functional>`, a mutable access observer,
and calls for demand vector/list accesses in the existing search functions.
It does not replace heap operations, tie handling or search bounds. The observer
is single-threaded and cleared by the adapter after each search. Existing vendor
choices predating the review are retained. Tests compare the observed search to
an independently constructed index using unobserved stock search.

`git diff 40d0edd -- sprint1/third_party/hnswlib/hnswalg.h` shows the observer patch.
The current artifact's provenance hashes identify the exact source needed for
reproduction even though the old upstream version is unknown.

The maintained build defines `HNSWLIB_USE_PREFETCH=0`. AddressSanitizer found an
out-of-bounds read while the vendor code computes a look-ahead prefetch address
at the end of a neighbour list. Disabling this optional prefetch path preserves
SIMD distance arithmetic and the search algorithm; final-source reproduction
checks compare traces/results against the recorded experiment.
