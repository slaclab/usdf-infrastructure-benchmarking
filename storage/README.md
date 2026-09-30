# storage

Read benchmarks for POSIX and S3. Results: `storage/results/`.

## Profiles

`profiles.yaml` defines endpoints; values come from the environment.

| Profile | Environment |
|---|---|
| `posix` | `IBENCH_POSIX_ROOT` |
| `s3` | `IBENCH_S3_ENDPOINT`, `IBENCH_S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (or `IBENCH_S3_ANON=1`), optional `AWS_REGION` |

A comma-separated `IBENCH_S3_ENDPOINT` spreads requests round-robin over several endpoints (micro benchmarks only).
The endpoint list is part of a result's series, so runs with one, two or more endpoints are tracked separately.

## Scenarios

A scenario is config only: `scenarios/<name>/scenario.yaml`.

| Scenario | Runs | Needs |
|---|---|---|
| [`s3-remote-read`](scenarios/s3-remote-read) | throughput vs concurrency, hot and cold latency, bulk | `IBENCH_S3_KEY`, `IBENCH_S3_PREFIX` |
| [`mixed-load`](scenarios/mixed-load) | sustained large reads and small latency-sensitive reads, alone and together | `IBENCH_S3_PREFIX` |
| [`parquet-training`](scenarios/parquet-training) | MLPerf parquet reads swept over partition size, workers, batch size, clients | `mpirun`, MLPerf setup |
| [`mlperf-baseline`](scenarios/mlperf-baseline) | stock MLPerf UNet3D, 1 to 32 simulated accelerators | `mpirun`, MLPerf setup |

```bash
uv run ibench-storage run s3-remote-read --profile s3 --client <label>     # every micro step of a scenario
uv run ibench-storage mix mixed-load     --profile s3 --client <label>     # alone vs together, plus ratios
```

## Micro benchmarks

```bash
uv run ibench-storage micro throughput --profile s3 --key <object> --levels 1,4,16,32,64
uv run ibench-storage micro latency    --profile s3 --key <object> --size 65536 -n 2000              # hot, one object
uv run ibench-storage micro latency    --profile s3 --prefix <dir/> --size 65536 -n 2000 --concurrency 8   # many objects
uv run ibench-storage micro bulk       --profile s3 --prefix <dir/> --concurrency 32 --max-gb 50
```

Throughput reads one object with parallel 8 MiB ranged reads into a null sink (no disk writes); MB is 1e6 bytes.
`--duration S` makes `latency` and `bulk` run for S seconds instead of a fixed count. Use `-n 1000` or more for a
meaningful P99.

## Mixed load and scaling

`mix` runs every load in `scenario.yaml` alone, then all together in separate processes with a shared start, and
writes `mix.<load>.ratio` (together over alone). To split loads across hosts, pick a start time a few minutes ahead
(`T=$(date -d '+5 min' +%s)`) and start one load on each host with the same value:

```bash
uv run ibench-storage mix mixed-load --profile s3 --only sequential --start-at $T    # host A
uv run ibench-storage mix mixed-load --profile s3 --only small      --start-at $T    # host B
```

These records are named `micro.<test>.<load>.together`; the same command without `--start-at` records
`micro.<test>.<load>.solo`, the baseline to compare against.

Gateway scaling: run one load with one endpoint, then with two or more (`IBENCH_S3_ENDPOINT=https://a,https://b`)
and compare aggregate throughput.

## MLPerf scenarios

Stock MLPerf Storage driven by scenario YAML. One-time setup clones `mlcommons/storage` at a pinned commit and
installs it from its own lockfile (which pins the DLIO fork with parquet support):

```bash
storage/scripts/setup_mlperf.sh        # needs git, uv and mpirun
uv run ibench-storage mlperf datagen parquet-training --profile posix --run base    # write a dataset once
uv run ibench-storage mlperf run     parquet-training --profile posix --cache cold
uv run ibench-storage mlperf configview parquet-training --profile posix            # resolved config, no run
```

`--profile s3` puts datasets under `s3://$IBENCH_S3_BUCKET/ibench/<scenario>/<dataset>` (one signed endpoint).
`--run NAME` selects one run (`datagen`: only the datasets it needs); `--mem-factor F` resizes datasets.

- Accelerators are simulated by DLIO; no GPU is used. All modes are `whatif`: for characterisation, not submission.
- Dataset size is `mem_factor` x client RAM so reads miss the page cache. MLPerf rule 3.1.2 requires 5x.
- Headline metric `train_io_mean_MB_per_second` is computed in MiB/s. With `train.computation_time: 0`, accelerator
  utilisation is meaningless; read I/O throughput.
- Environment: `IBENCH_RAW_DIR` (engine output), `MLPSTORAGE_BIN`, `MLPSTORAGE_REF`, `MLPSTORAGE_EXTRA` (extra
  flags), `IBENCH_MEM_GIB` (override detected RAM; otherwise Slurm allocation, cgroup limit, then MemTotal).

## Gotchas

- Engine output (`IBENCH_RAW_DIR`) must be on a different filesystem than the dataset (MLPerf CAP-03).
- DLIO refuses runs whose workers (`read_threads` x accelerators, about 0.5 GB each for parquet) exceed node memory;
  lower `reader.read_threads`.
- Record `--cache cold|warm`; a tiered filesystem can vary several-fold between them.
- The micro benchmark is a Python thread pool; above about 32 threads the GIL costs throughput. Cross-check high
  numbers with MLPerf or `rclone`.
- Loads in `mix` that cycle over a small prefix are served from cache after the first pass; size `max_gb` above the
  cache or record `--cache warm`.
