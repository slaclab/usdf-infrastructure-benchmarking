# usdf-infrastructure-benchmarking

Network and storage benchmarks with one consolidated performance history. Every run writes a JSON record;
`reports/` turns the records into a latest-state table and a history that flags regressions.

## Install

```bash
uv sync
uv run pytest -q
```

Needs `git` and [`uv`](https://docs.astral.sh/uv/) (fetches Python 3.12). `iperf3` is needed for the network suite and
`mpirun` for the MLPerf scenarios only.

## Suites

| Suite | Runs | Details |
|---|---|---|
| [`network/`](network) | iperf3 stream sweeps, RTT, loss, path MTU | [network/README.md](network/README.md) |
| [`storage/`](storage) | read micro benchmarks (POSIX, S3), mixed-load interference, stock [MLPerf Storage](https://github.com/mlcommons/storage) scenarios | [storage/README.md](storage/README.md) |
| [`reports/`](reports) | `latest.md`, `history.csv`, plots | [reports/README.md](reports/README.md) |

## Run

Targets are set by environment variables; S3 credentials come from `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`
(or `IBENCH_S3_ANON=1` for a public bucket).

| Variable | Meaning |
|---|---|
| `IBENCH_S3_ENDPOINT`, `IBENCH_S3_BUCKET` | S3 target; several endpoints may be comma-separated |
| `IBENCH_S3_KEY`, `IBENCH_S3_PREFIX` | one large object and a directory of objects used by the scenarios |
| `IBENCH_POSIX_ROOT` | directory on the filesystem under test |

```bash
uv run ibench-net path  <host>                                   # RTT, loss, path MTU
uv run ibench-net iperf <host> --streams 1,8,16                  # needs `iperf3 -s` on <host>
uv run ibench-storage run s3-remote-read --profile s3 --client <label>
uv run ibench-storage mix mixed-load     --profile s3 --client <label>
uv run ibench-report build                                       # reports/latest.md, reports/history.csv
```

Label every run with `--client <vantage point>`; add `--tag key=value` for system state (`gateway=new`) and
`--cache cold|warm` for cache state.

### Slurm

```bash
srun -p hopper -A rubin:developers --qos=normal --gres=gpu:1 --pty bash      # interactive
sbatch slurm/job.sh ibench-storage run s3-remote-read --profile s3            # batch
```

The GPU request only places the job; nothing here uses it. Default CPU and memory shares cap thread-pool throughput, so
add `--cpus-per-task` and `--mem` for throughput runs; the record stores the allocation. Other clusters: override
`-p`, `-A` and friends on the `sbatch` line, or run without Slurm.

### Another site

Nothing is tied to one cluster: clone, `uv sync`, export the variables above, and run. POSIX scenarios need the
filesystem mounted; S3, network and report commands do not. Copy the new `*/results/*.json` files into the same
folders of a checkout and run `uv run ibench-report build`.

## Results

Per-run JSON (metrics, parameters, host, kernel TCP settings, allocation, git SHA) goes to `network/results/` or
`storage/results/`. `reports/latest.md` lists each series with its previous value, change and status (regressions
first); `reports/history.csv` has every run. `reports/legacy/` seeds the history with earlier measurements, each citing
its source.
