# genesis/parquet-reads

Raw read ceiling for 300-600 MB parquet partitions: whole-file reads over a concurrency sweep, and 1 MiB ranged
reads (row-group sized) with P99 latency. Runs on `--profile s3` (warp) and `--profile posix` (fio), so the two
paths are comparable.

```bash
uv run ibench-storage mkdata genesis/parquet-reads --profile s3
uv run ibench-storage run    genesis/parquet-reads --profile s3 --client <label> --repeat 3
uv run ibench-storage run    genesis/parquet-reads --profile posix --client <label> --cache cold
```

The MLPerf training emulation over the same data shape is [`parquet-training`](../parquet-training).
