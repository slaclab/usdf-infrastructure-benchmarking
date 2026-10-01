# reports

The consolidated view: where performance stands now and how it has moved.

```bash
uv run ibench-report build             # writes latest.md and history.csv
uv run ibench-report build --plots     # also plots/*.png (uv sync --extra plots)
```

- `latest.md`: latest value per series with previous value, change, best and status. A series is
  suite / test / scenario / profile / target / client / cache, so a different vantage point, endpoint list or cache
  state starts a new series. Regressions (worse than the previous run by more than `--threshold`, default 10%) come first.
- `history.csv`: one row per run, all series.
- `intake/network.csv`: hand-entered network numbers, one row per measurement (below).
- `legacy/`: earlier measurements in the same schema, each citing its source; some are transcribed from chat and
  marked so.

Runs repeated with `--repeat N` share a session and appear as one point: the median, with n and the min-max range in
`latest.md`; `history.csv` keeps every run.

Interference runs appear as `mix.<load>.ratio` (together over alone): below 1 for throughput or above 1 for latency is
interference.

Generated files are committed so the history is reviewable in git.

## Adding numbers by hand

Append rows to `intake/network.csv` (a spreadsheet can edit and export it). Rows are checked on `build`; an error names
the line. Do not put names in any column; cite a ticket, channel or document in `source`.

| Column | Required | Meaning |
|---|---|---|
| `date` | yes | day of the measurement, `YYYY-MM-DD` |
| `source` | yes | ticket, Slack channel or document the number comes from, or `own run` |
| `scope` | yes | `wan` (across the internet or a cloud) or `internal` (within the site) |
| `client` | yes | where the traffic started or was read, e.g. `gcp-us-central1-tier1`, `sdfiana028-031` |
| `target` | yes | what was measured against, e.g. `sdfdatas3`, `sdfemb101-203`, `s3df-dtn` |
| `direction` | yes | `to-server` (client sends) or `from-server` (client receives) |
| `value` | yes | the aggregate result (all streams and pairs together) |
| `unit` | no | `Gbps` (default), `Mbps`, `GB/s`, `MB/s`, `GiB/s`, `MiB/s`; converted to Gbps |
| `tool` | no | `iperf3` (default), `warp`, `locust`, ... |
| `streams` | no | parallel streams per host pair (`-P`) |
| `pairs` | no | host pairs run together |
| `duration_s`, `mtu`, `state`, `note` | no | kept for reference, e.g. `state` = `before gateway change` |

Rows with the same tool, streams, pairs, direction, target, scope and client form one series: the report compares the
newest with the previous one, so keep those the same when repeating a test.
