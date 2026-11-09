#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export XDG_CACHE_HOME="$ROOT/.toolchain/cache"
export XDG_CONFIG_HOME="$ROOT/.toolchain/config"
TECTONIC="${TECTONIC:-$ROOT/.toolchain/bin/tectonic}"
if [[ ! -x "$TECTONIC" ]]; then
  TECTONIC="$(command -v tectonic)"
fi
BUNDLE="https://data1b.fullyjustified.net/tlextras-2022.0r0.tar"
FLAGS=(--web-bundle "$BUNDLE" --keep-logs)
if [[ "${TECTONIC_OFFLINE:-0}" == "1" ]]; then FLAGS+=(--only-cached); fi
"$TECTONIC" "${FLAGS[@]}" doc/pim_ann_thesis.tex
"$TECTONIC" "${FLAGS[@]}" doc/pim_ann_ieee.tex
python3 scripts/check_docs.py
