# interference/dac-vs-genesis

Three loads on one endpoint: `dac_images` (whole-image reads, Gbps), `dac_tiles` (small-object reads, P99 time to
first byte) and `genesis` (bulk partition reads, Gbps). Each runs alone, then all together; `mix.<load>.ratio` is the
change (together over alone: below 1 for throughput or above 1 for latency is interference).

```bash
uv run ibench-storage mkdata interference/dac-vs-genesis --profile s3
uv run ibench-storage mix    interference/dac-vs-genesis --profile s3 --client <label> --repeat 3
```

To test two loads against each other, or to put the loads on different hosts, pick a start time a few minutes ahead
and start one load per host with the same value:

```bash
T=$(date -d '+5 min' +%s)
uv run ibench-storage mix interference/dac-vs-genesis --profile s3 --only genesis   --start-at $T   # host A
uv run ibench-storage mix interference/dac-vs-genesis --profile s3 --only dac_tiles --start-at $T   # host B
```

These records are named `read.<load>.together`; the same command without `--start-at` records `read.<load>.solo`, the
baseline. For gateway scaling, run one load with one endpoint and again with several
(`IBENCH_S3_ENDPOINT=https://a,https://b`); the endpoint list is part of a result's series.
Loads start together but each warp lists its objects first, so allow a few seconds of skew at the start of a run.
