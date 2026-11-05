# genesis/hats-reads

Reads four columns (`column`, `ra`, `dec`, `_healpix_29`) of the same partitions of a HATS catalog with pyarrow
(to Arrow, to numpy-backed pandas, to Arrow-backed pandas), nested-pandas and lsdb, and on S3 also with pyarrow's
native S3 client. The same code runs over `--profile posix` and `--profile s3`, so the two paths are comparable.
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
- S3 reads use one endpoint: `IBENCH_S3_ENDPOINT` must not list several.
- Notebook version: [`storage/notebooks/hats_reads.ipynb`](../../../notebooks/hats_reads.ipynb), which calls the same
  code and writes the same records.
