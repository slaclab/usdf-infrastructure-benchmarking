# s3-remote-read

Reads from an S3 endpoint: throughput vs concurrency on one large object, hot single-object latency, cold many-object
latency, bulk transfer. Steps are in `scenario.yaml`.

```bash
export IBENCH_S3_ENDPOINT=... IBENCH_S3_BUCKET=... IBENCH_S3_KEY=<object, 1 GiB or more> IBENCH_S3_PREFIX=<dir/>
uv run ibench-storage run s3-remote-read --profile s3 --client <label> --cache warm
```

Run it from each vantage point and compare in `reports/`.
