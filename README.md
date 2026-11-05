# usdf-infrastructure-benchmarking

Network and storage benchmarks with one consolidated performance history. Every run writes a JSON record;
`reports/` turns the records into a latest-state table and a history that flags regressions.

## Install

```bash
uv sync
uv run pytest -q
storage/scripts/setup_tools.sh      # warp (S3 reads) and a check for fio (POSIX reads)
uv sync --extra hats                # also lsdb, hats and s3fs, for the HATS read scenario
```

Needs `git` and [`uv`](https://docs.astral.sh/uv/) (fetches Python 3.12). `iperf3` is needed for the network suite,
[`warp`](https://github.com/minio/warp) for S3 profiles, `fio` for POSIX profiles and `mpirun` for the MLPerf scenarios only.

## Suites

| Suite | Runs | Details |
|---|---|---|
| [`network/`](network) | iperf3 stream sweeps, RTT, loss, path MTU | [network/README.md](network/README.md) |
| [`storage/`](storage) | scenarios per use case: Rubin object reads, Genesis parquet reads and tokenization, interference, stock [MLPerf Storage](https://github.com/mlcommons/storage) | [storage/README.md](storage/README.md) |
| [`reports/`](reports) | `latest.md`, `history.csv`, plots | [reports/README.md](reports/README.md) |
| [`sites/`](sites) | one YAML description per vantage point, stored with each result | [sites/template.yaml](sites/template.yaml) |

## Run

Targets are set by environment variables; S3 credentials come from `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.
warp has no anonymous mode, so S3 profiles need a key pair.

| Variable | Meaning |
|---|---|
| `IBENCH_S3_ENDPOINT`, `IBENCH_S3_BUCKET` | S3 target; several endpoints may be comma-separated |
| `IBENCH_S3_LOOKUP` | `path` (default) or `host` for virtual-hosted-style buckets |
| `IBENCH_DATA_PREFIX` | where mock data lives in the bucket or under the POSIX root (default `ibench/data`) |
| `IBENCH_POSIX_ROOT` | directory on the filesystem under test |

```bash
uv run ibench-net path  <host>                                   # RTT, loss, path MTU
uv run ibench-net iperf <host> --streams 1,8,16                  # needs `iperf3 -s` on <host>
uv run ibench-storage mkdata rubin-access/object-reads --profile s3 --scale 0.05   # mock payloads, once
uv run ibench-storage run rubin-access/object-reads --profile s3 --client <label> --repeat 3
uv run ibench-storage mix interference/dac-vs-genesis --profile s3 --client <label>
uv run ibench-storage hats genesis/hats-reads --profile s3 --client <label>     # HATS catalog reads; notebook: storage/notebooks/
uv run ibench-report build                                       # reports/latest.md, reports/history.csv
```

Label every run with `--client <vantage point>`; add `--tag key=value` for system state (`gateway=new`) and
`--cache cold|warm` for cache state. `--repeat N` runs a scenario N times; the report shows the median with n and range.

### Slurm

```bash
srun -p hopper -A rubin:developers --qos=normal --gres=gpu:1 --pty bash      # interactive
sbatch slurm/job.sh ibench-storage run rubin-access/object-reads --profile s3   # batch
```

The GPU request only places the job; nothing here uses it. Default CPU and memory shares cap thread-pool throughput, so
add `--cpus-per-task` and `--mem` for throughput runs; the record stores the allocation. Other clusters: override
`-p`, `-A` and friends on the `sbatch` line, or run without Slurm.

### Another site

Nothing is tied to one cluster: clone, `uv sync`, run `storage/scripts/setup_tools.sh`, export the variables above and
run. Copy `sites/template.yaml` to `sites/<client label>.yaml` and fill it in; it is stored with every result from that
client. POSIX scenarios need the filesystem mounted; S3, network and report commands do not. Copy the new
`*/results/*.json` files into the same folders of a checkout and run `uv run ibench-report build`.

## Related load tests

- [embargo-loadsim](https://github.com/lsst-dm/embargo-loadsim): Locust simulator of the observatory visit workload
  (bursty writes, calibration preloads, readback, pipeline write-out) for S3 endpoints.
- [usdf_benchmarks](https://github.com/slaclab/usdf_benchmarks): load tests driven through HTCondor and Slurm.

This repo's storage scenarios measure reads and interference through the gateways; use the simulator for write-heavy
or time-structured loads.

## Results

Per-run JSON (metrics, parameters, host, site description, kernel TCP settings, allocation, git SHA and uv.lock hash,
tool name, version and command) goes to `network/results/` or `storage/results/`. Raw tool output stays in
`storage/results/raw/` (not committed); each record names the file. `reports/latest.md` lists each series with its
previous value, change and status (regressions first); `reports/history.csv` has every run. `reports/legacy/` seeds the
history with earlier measurements, each citing its source.
