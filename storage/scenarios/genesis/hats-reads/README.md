# genesis/hats-reads

Reads four columns (`column`, `ra`, `dec`, `_healpix_29`) of the same partitions of a HATS catalog with pyarrow
(to Arrow, to numpy-backed pandas, to Arrow-backed pandas), nested-pandas and lsdb, and on S3 also with pyarrow's
native S3 client (`pa_arrow_native`) and pyarrow over fsspec with planned column ranges (`pa_arrow_ranges`). The same code runs over `--profile posix` and `--profile s3`, so the two paths are comparable.
Every reader reduces to the mean of `column`; the run fails if they disagree.

Also recorded: `hats.stat` (time to stat one partition: S3 HEAD or POSIX stat) and `hats.ceiling.t<N>` (parallel
64 MiB ranged reads of whole partitions with no decoding, the most this client can pull at N threads; holds up to
N x 64 MiB in memory).

Needs the `hats` extra:

```bash
uv sync --extra hats
export IBENCH_S3_ENDPOINT=https://<gateway> IBENCH_S3_BUCKET=<bucket> AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
export IBENCH_POSIX_ROOT=<directory holding the same tree as the bucket>
uv run ibench-storage hats genesis/hats-reads --profile s3 --client <label> --repeat 3
uv run ibench-storage hats genesis/hats-reads --profile posix --client <label> --cache cold
```

- The catalog is a path relative to the bucket or POSIX root (`IBENCH_HATS_CATALOG`, `--catalog`; default
  `lsdb/gaia_dr3/gaia`). Only partitions present under it are read, in pixel order, after `--offset` and up to
  `--partitions` (0 = all present).
- `--threads 4,8,16` sweeps thread counts; a record name carries `.t<N>` when several are given and `.n<partitions>`
  always, because those change the series.
- The primary metric is `gbps`: compressed bytes of the four columns over wall time. `wire_mb` is the payload fetched
  over S3 and `over_read` its ratio to `need_mb`; the native pyarrow reader is not counted.
- A warm pass runs first (connections, gateway and filesystem caches); `--no-warm` skips it. Over POSIX, a cold read
  needs partitions no process on the node has read (`--offset`); `posix_fadvise` does not evict Weka's cache.
- On S3 the `pa_*` readers without `ranges` or `native` go through s3fs's default read-ahead cache, which fetches far
  more than the columns need (`over_read` in the tens) and is slow over a WAN; they show what a plain
  `pd.read_parquet("s3://...")` gets. Pick readers with `--variants lsdb,npd_direct,pa_arrow_native` to skip them.
- S3 reads use one endpoint: `IBENCH_S3_ENDPOINT` must not list several.

## From Python

The command line calls `ibench_storage.hats.run`, which can be used directly. It returns one record per reader,
the stat latency and the ceiling levels; `ibench.cli.finish` writes them to `storage/results/`.

```python
from ibench_storage import hats, profiles, scenario

prof = profiles.load("s3")  # or "posix"
spec = {**scenario.load("genesis/hats-reads")["hats"], "partitions": 192, "threads": [8],
        "variants": ["lsdb", "npd_direct", "pa_arrow_native"], "ceiling": []}
for run in hats.run(prof, spec, "genesis/hats-reads"):
    print(run.name, run.metrics.get("wall_s"), run.primary)
```

The S3 setup (s3fs, `UPath` and pyarrow clients, byte counting) is `Source._init_s3` in
[`hats.py`](../../../src/ibench_storage/hats.py), and the readers are `_variants` in the same file.

## Notebooks

Register the environment as a kernel (`uv run --extra hats python -m ipykernel install --user --name ibench`).

- [`hats_reads.ipynb`](../../../notebooks/hats_reads.ipynb) runs this scenario and writes the same records as the
  command line.
- [`hats_reads_s3.ipynb`](../../../notebooks/hats_reads_s3.ipynb) is a self-contained walkthrough of the S3 readers,
  with a comment on each step and no imports from this repository. Set `IBENCH_S3_ENDPOINT`, `IBENCH_S3_BUCKET`,
  `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`; optional `IBENCH_HATS_CATALOG`, `IBENCH_HATS_PARTITIONS` and
  `IBENCH_HATS_THREADS`.
