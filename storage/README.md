# storage

Storage benchmarks per use case, built on existing tools: [warp](https://github.com/minio/warp) for S3 reads,
[fio](https://fio.readthedocs.io) for POSIX reads, stock [MLPerf Storage](https://github.com/mlcommons/storage) for
training, and a small harness for tokenization. Results: `storage/results/`; raw tool output: `storage/results/raw/`.

## Profiles

`profiles.yaml` defines endpoints; values come from the environment.

| Profile | Environment |
|---|---|
| `posix` | `IBENCH_POSIX_ROOT` |
| `s3` | `IBENCH_S3_ENDPOINT`, `IBENCH_S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, optional `AWS_REGION`, `IBENCH_S3_LOOKUP` |

A comma-separated `IBENCH_S3_ENDPOINT` spreads requests round-robin over several endpoints. The endpoint list is part
of a result's series, so runs with one, two or more endpoints are tracked separately.

## Scenarios

A scenario is config only: `scenarios/<group>/<name>/scenario.yaml`. Payload classes and sizes are in `datasets.yaml`.

| Scenario | Runs | Command |
|---|---|---|
| [`rubin-access/object-reads`](scenarios/rubin-access/object-reads) | images, coadds, raw archives, ranged table reads, cutout-sized ranges, small tiles | `run` |
| [`genesis/parquet-reads`](scenarios/genesis/parquet-reads) | parquet partitions swept over concurrency; row-group-sized ranges | `run` |
| [`genesis/tokenization`](scenarios/genesis/tokenization) | read text shards, tokenize, write token shards | `tokens` |
| [`interference/dac-vs-genesis`](scenarios/interference/dac-vs-genesis) | image and tile reads alone, bulk parquet alone, then all together | `mix` |
| [`genesis/parquet-training`](scenarios/genesis/parquet-training) | MLPerf parquet reads swept over partition size, workers, batch size | `mlperf` |
| [`genesis/mlperf-baseline`](scenarios/genesis/mlperf-baseline) | stock MLPerf UNet3D, 1 to 32 simulated accelerators | `mlperf` |

```bash
uv run ibench-storage mkdata <scenario> --profile s3 --dry-run       # size first; --scale 0.05 for a smoke test
uv run ibench-storage mkdata <scenario> --profile s3                 # write the payloads (needs write access)
uv run ibench-storage run    <scenario> --profile s3 --client <label> --repeat 3
uv run ibench-storage get    --profile s3 --prefix <dir/> --concurrency 1,8,32 --duration 60   # existing data
uv run ibench-storage mix    interference/dac-vs-genesis --profile s3 --client <label>
uv run ibench-storage tokens genesis/tokenization --profile s3 --client <label>
```

`mkdata` refuses to write more than `--max-gb` (default 200) and skips objects that exist, so a rerun resumes.
`get` accepts `--range-kib N` (random ranged reads), `--metric latency` and, for POSIX, `--direct`.

Reads use warp (S3) or fio (POSIX) and never write to the target: warp runs with `--list-existing --noclear`, fio with
`--allow_file_create=0`. Throughput steps report Gbps (1e9 bits/s). Latency steps report P99 time to first byte (S3) or
I/O completion latency (POSIX).

## Interference

`mix` runs every load in `scenario.yaml` alone, then all together, and writes `mix.<load>.ratio` (together over
alone). To split loads across hosts, pick a start time a few minutes ahead (`T=$(date -d '+5 min' +%s)`) and start one
load on each host with the same value:

```bash
uv run ibench-storage mix interference/dac-vs-genesis --profile s3 --only dac_tiles --start-at $T   # host A
uv run ibench-storage mix interference/dac-vs-genesis --profile s3 --only genesis   --start-at $T   # host B
```

Gateway scaling: run one load with one endpoint, then with two or more (`IBENCH_S3_ENDPOINT=https://a,https://b`)
and compare aggregate throughput.

## MLPerf scenarios

Stock MLPerf Storage driven by scenario YAML. One-time setup clones `mlcommons/storage` at a pinned commit and
installs it from its own lockfile (which pins the DLIO fork with parquet support):

```bash
storage/scripts/setup_mlperf.sh        # needs git, uv and mpirun
uv run ibench-storage mlperf datagen genesis/parquet-training --profile posix --run base
uv run ibench-storage mlperf run     genesis/parquet-training --profile posix --cache cold
uv run ibench-storage mlperf configview genesis/parquet-training --profile posix
```

`--profile s3` puts datasets under `s3://$IBENCH_S3_BUCKET/ibench/<scenario>/<dataset>` (one signed endpoint).
`--run NAME` selects one run (`datagen`: only the datasets it needs); `--mem-factor F` resizes datasets.

- Accelerators are simulated by DLIO; no GPU is used. All modes are `whatif`: for characterisation, not submission.
- Dataset size is `mem_factor` x client RAM so reads miss the page cache. MLPerf rule 3.1.2 requires 5x; size the
  bucket quota for it.
- Headline metric `train_io_mean_MB_per_second` is computed in MiB/s. With `train.computation_time: 0`, accelerator
  utilisation is meaningless; read I/O throughput.
- Environment: `IBENCH_RAW_DIR` (engine output), `MLPSTORAGE_BIN`, `MLPSTORAGE_REF`, `MLPSTORAGE_EXTRA` (extra
  flags), `IBENCH_MEM_GIB` (override detected RAM; otherwise Slurm allocation, cgroup limit, then MemTotal).

## Gotchas

- warp empties its bucket by default; this harness always passes `--noclear`. Do not run warp by hand against a bucket
  with data in it without `--list-existing --noclear`.
- A run shorter than a few seconds gives warp too few samples; keep `duration_s` at 30 or more.
- POSIX reads go through the page cache unless `--direct`; record `--cache cold|warm`. A tiered filesystem can vary
  several-fold between them.
- warp and fio measure different paths (HTTP through a gateway vs a mounted filesystem); compare them as indications,
  not as a like-for-like pair.
- The tokenization harness uses a small BPE trained on the first shard, so `tokens_per_s` compares storage and CPU
  configurations; it is not a model-specific tokenization speed. `io_share` is the fraction of worker time spent in
  reads and writes.
- Engine output (`IBENCH_RAW_DIR`) must be on a different filesystem than the MLPerf dataset (MLPerf CAP-03).
- DLIO refuses runs whose workers (`read_threads` x accelerators, about 0.5 GB each for parquet) exceed node memory;
  lower `reader.read_threads`.
- Loads in `mix` that cycle over a small prefix are served from cache after the first pass; size the data above the
  cache or record `--cache warm`.
