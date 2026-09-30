#!/usr/bin/env bash
# Build the stock MLPerf Storage engine from its own lockfile (Python 3.12, Linux) under .vendor/.
# The lockfile pins the DLIO fork with parquet support, so do not substitute PyPI's dlio-benchmark.
# Needs git, uv and an MPI runtime (mpirun) on the node that runs the benchmark.
set -euo pipefail

REF="${MLPSTORAGE_REF:-ab2b2e9d8dcb2b2cb499e66c163bfba572153e16}"  # mlcommons/storage main, 2026-09-23
SRC="$(cd "$(dirname "$0")/../.." && pwd)/.vendor/mlcommons-storage"

mkdir -p "$(dirname "$SRC")"
[ -d "$SRC/.git" ] || git clone https://github.com/mlcommons/storage.git "$SRC"
git -C "$SRC" fetch --quiet origin
git -C "$SRC" checkout --quiet "$REF"

cd "$SRC"
uv sync --frozen  # editable install: mlpstorage reads its workload YAMLs from this checkout
command -v mpirun >/dev/null || echo "warning: mpirun not found; load an MPI module or install OpenMPI" >&2
.venv/bin/mlpstorage version
