# mixed-load

Two loads on one endpoint: `sequential` (sustained large-object reads, reports Gbps) and `small` (small reads, reports
P99 latency). Each runs alone, then both together; `mix.<load>.ratio` is the change.

```bash
export IBENCH_S3_ENDPOINT=... IBENCH_S3_BUCKET=... IBENCH_S3_PREFIX=<dir/>
uv run ibench-storage mix mixed-load --profile s3 --client <label>
```

Edit `scenario.yaml` to change a load (concurrency, size, duration_s) or add one; every load needs `duration_s`.
Loads split across hosts: see [storage/README.md](../../README.md#mixed-load-and-scaling).
