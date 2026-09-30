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
- `legacy/`: earlier measurements in the same schema, each citing its source; some are transcribed from chat and
  marked so.

Mixed-load runs appear as `mix.<load>.ratio` (together over alone): below 1 for throughput or above 1 for latency is
interference.

Generated files are committed so the history is reviewable in git.
