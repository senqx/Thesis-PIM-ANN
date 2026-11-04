#!/usr/bin/env bash
# =============================================================================
# setup_ramulator.sh
# Reproducible, from-scratch build of Ramulator 2.1 (CMU-SAFARI) + run our ANN
# memory traces through its cycle-accurate HBM2 model.
#
# This script encodes every workaround we discovered building it in a locked-down
# sandbox. On a normal VM with a real internet connection it is mostly a
# convenience wrapper; the pre-clone-deps logic also makes it robust on machines
# where CMake's FetchContent is slow or blocked.
#
# Usage:
#   ./setup_ramulator.sh                 # full build, then run both ANN traces
#   RAMULATOR_DIR=~/ramulator2 ./setup_ramulator.sh
#
# Requirements it will check / use:
#   - git, a C++20 compiler (g++ 11+ or clang++ 15+), python3 (3.10+) with dev
#     headers, and CMake >= 3.14. If cmake is missing, it downloads a prebuilt
#     Kitware binary into ./.toolchain (no root needed).
# =============================================================================
set -euo pipefail

# ---- config ----------------------------------------------------------------
RAMULATOR_REPO="https://github.com/CMU-SAFARI/ramulator2.git"
RAMULATOR_DIR="${RAMULATOR_DIR:-$PWD/ramulator2}"
TOOLCHAIN_DIR="$PWD/.toolchain"
CMAKE_VER="3.30.5"
# dependency pins used by Ramulator 2.1 (match its CMakeLists)
FMT_TAG="10.2.1"
YAMLCPP_TAG="yaml-cpp-0.9.0"
NANOBIND_TAG="v2.4.0"
JOBS="$(nproc 2>/dev/null || echo 4)"

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# ---- 0. sanity: compiler + python -----------------------------------------
say "Checking toolchain"
command -v git >/dev/null || die "git not found. Install it (Arch: sudo pacman -S git)."
command -v g++ >/dev/null || command -v clang++ >/dev/null || die "No C++ compiler found."
command -v python3 >/dev/null || die "python3 not found."
python3 -c 'import sysconfig,sys; sys.exit(0 if sysconfig.get_paths().get("include") else 1)' \
  || die "python3 dev headers missing (Arch: python is enough; Debian: sudo apt install python3-dev)."

# Verify C++20
echo 'int main(){return 0;}' | ${CXX:-g++} -std=c++20 -x c++ - -o /tmp/_cxx20check 2>/dev/null \
  && rm -f /tmp/_cxx20check || die "Compiler does not support C++20. Upgrade g++ (>=11) or clang (>=15)."

# ---- 1. ensure cmake (download prebuilt if needed) -------------------------
if command -v cmake >/dev/null && cmake --version | head -1 | grep -qE '3\.(1[4-9]|[2-9][0-9])'; then
  CMAKE="cmake"
  say "Using system cmake: $(cmake --version | head -1)"
else
  say "CMake >=3.14 not found — fetching prebuilt $CMAKE_VER into .toolchain"
  mkdir -p "$TOOLCHAIN_DIR"
  TARBALL="cmake-${CMAKE_VER}-linux-x86_64.tar.gz"
  URL="https://github.com/Kitware/CMake/releases/download/v${CMAKE_VER}/${TARBALL}"
  # resumable download (handles flaky / time-limited connections)
  for i in 1 2 3 4 5; do
    curl -fsSL -C - -o "$TOOLCHAIN_DIR/$TARBALL" "$URL" || true
    if tar tzf "$TOOLCHAIN_DIR/$TARBALL" >/dev/null 2>&1; then break; fi
    say "download attempt $i incomplete, resuming..."
  done
  tar xzf "$TOOLCHAIN_DIR/$TARBALL" -C "$TOOLCHAIN_DIR"
  CMAKE="$TOOLCHAIN_DIR/cmake-${CMAKE_VER}-linux-x86_64/bin/cmake"
  "$CMAKE" --version | head -1
fi

# ---- 2. clone Ramulator ----------------------------------------------------
if [ ! -d "$RAMULATOR_DIR/.git" ]; then
  say "Cloning Ramulator 2.1 -> $RAMULATOR_DIR"
  git clone --depth 1 "$RAMULATOR_REPO" "$RAMULATOR_DIR"
else
  say "Ramulator already present at $RAMULATOR_DIR"
fi
cd "$RAMULATOR_DIR"

# ---- 3. pre-clone deps into ext/ and switch CMake to add_subdirectory ------
# Why: Ramulator's CMakeLists uses FetchContent (git clone at configure time),
# which can stall on slow/limited connections. Pre-cloning + add_subdirectory
# makes the build offline-friendly and reliable.
preclone() { # name url tag [--recurse]
  local name="$1" url="$2" tag="$3" recurse="${4:-}"
  if [ ! -f "ext/$name/CMakeLists.txt" ]; then
    say "Pre-cloning $name@$tag"
    rm -rf "ext/$name"
    git clone --depth 1 --branch "$tag" $recurse "$url" "ext/$name"
  fi
}
preclone fmt      "https://github.com/fmtlib/fmt.git"        "$FMT_TAG"
preclone yaml-cpp "https://github.com/jbeder/yaml-cpp.git"   "$YAMLCPP_TAG"
preclone nanobind "https://github.com/wjakob/nanobind.git"   "$NANOBIND_TAG" "--recurse-submodules --shallow-submodules"

if ! grep -q 'add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/ext/fmt)' CMakeLists.txt; then
  say "Patching CMakeLists.txt: FetchContent -> add_subdirectory"
  cp CMakeLists.txt CMakeLists.txt.orig
  python3 - <<'PY'
import re
f="CMakeLists.txt"; t=open(f).read()
def repl(block_start_marker, decl_name, src):
    # replace a FetchContent_Declare(...)+MakeAvailable(...) block with add_subdirectory
    import re
    pat = re.compile(
        r"FetchContent_Declare\(\s*%s.*?FetchContent_MakeAvailable\(\s*%s\s*\)\s*"
        r"(?:include_directories\([^\)]*\)\s*)?" % (re.escape(decl_name), re.escape(decl_name)),
        re.S)
    reptxt = ("add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/ext/%s)\n"
              "  include_directories(${CMAKE_CURRENT_SOURCE_DIR}/ext/%s/include)\n" % (src, src))
    return pat.sub(reptxt, t, count=1)
t = repl(None, "yaml-cpp", "yaml-cpp")
t = repl(None, "fmt", "fmt")
# nanobind: no include dir line
import re
t = re.sub(r"FetchContent_Declare\(\s*nanobind.*?FetchContent_MakeAvailable\(\s*nanobind\s*\)",
           "add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/ext/nanobind)", t, count=1, flags=re.S)
open(f,"w").write(t)
print("patched" if "add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/ext/fmt)" in t else "WARN: patch may be incomplete")
PY
fi

# ---- 4. configure + build (with Python bindings) ---------------------------
say "Configuring"
rm -rf build && mkdir build && cd build
"$CMAKE" .. >/dev/null
say "Building (this is the long step)"
"$CMAKE" --build . -j"$JOBS"
cd "$RAMULATOR_DIR"
[ -f libramulator.so ] || die "build produced no libramulator.so"
ls python/ramulator/_ramulator*.so >/dev/null 2>&1 || die "Python module not built."
say "Build OK: libramulator.so + Python module present"

# ---- 5. generate ANN traces + run through real Ramulator -------------------
say "Generating ANN traces and running them through Ramulator"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"            # Thesis-PIM-ANN/scripts
PROJ="$(dirname "$HERE")"                                        # Thesis-PIM-ANN
# build our trace generator if needed
if [ ! -x "$PROJ/bin/gen_trace" ]; then (cd "$PROJ" && make >/dev/null); fi
mkdir -p "$PROJ/traces"
"$PROJ/bin/gen_trace" --num_vectors 4096 --dim 128 --pattern seq  > "$PROJ/traces/ann_seq.trace"
"$PROJ/bin/gen_trace" --num_vectors 4096 --dim 128 --pattern rand > "$PROJ/traces/ann_rand.trace"

export PYTHONPATH="$RAMULATOR_DIR/python"
export LD_LIBRARY_PATH="$RAMULATOR_DIR"
echo
echo "================= SEQUENTIAL (IVF/PQ scan) ================="
python3 "$PROJ/scripts/run_ann_ramulator.py" "$PROJ/traces/ann_seq.trace"
echo
echo "================= RANDOM (graph/HNSW traversal) ============"
python3 "$PROJ/scripts/run_ann_ramulator.py" "$PROJ/traces/ann_rand.trace"
echo
say "Done. Expected shape: sequential ~94% row-hit (fast), random ~55% row-hit (slow, +~40% cycles)."
