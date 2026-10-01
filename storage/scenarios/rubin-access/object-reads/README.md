# rubin-access/object-reads

Read patterns of users fetching Rubin data over S3: whole images and coadds, raw archives, ranged reads of large
tables, cutout-sized ranges out of image files, and small tiles. Object sizes come from `storage/datasets.yaml`.
Throughput steps report Gbps; `cutouts` and `tiles` report P99 time to first byte.

```bash
export IBENCH_S3_ENDPOINT=https://<gateway> IBENCH_S3_BUCKET=<bucket> AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
uv run ibench-storage mkdata rubin-access/object-reads --profile s3 --dry-run     # size first
uv run ibench-storage mkdata rubin-access/object-reads --profile s3               # needs write access
uv run ibench-storage run    rubin-access/object-reads --profile s3 --client <label> --repeat 3
```

Run it from each vantage point; compare in `reports/`. To read existing data instead, use `ibench-storage get`.
