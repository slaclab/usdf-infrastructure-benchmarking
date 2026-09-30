# parquet-training

MLPerf Storage `flux` parquet workload with compute time set to 0: what storage delivers to concurrent workers that
read whole parquet partitions sequentially. Runs sweep partition size (150, 300, 600 MiB), reader threads, batch size
and client count around a base of 300 MiB / 8 threads / batch 48 / 4 clients.

```bash
storage/scripts/setup_mlperf.sh
uv run ibench-storage mlperf datagen parquet-training --profile posix --run base        # dataset per size: use --run
uv run ibench-storage mlperf run parquet-training --profile posix --cache cold          # all runs, or --run NAME
```

Each dataset is `mem_factor` (2) x client RAM; generate only the sizes you run. Rows use the stock `flux` schema
(2.16 MB per row, uncompressed) so partition size and layout are realistic but row contents are not.
