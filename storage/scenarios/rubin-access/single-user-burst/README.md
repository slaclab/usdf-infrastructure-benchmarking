# rubin-access/single-user-burst

One client downloads whole image objects in parallel at rising concurrency, the way a single user fetching a batch of
images does. Two steps run the same ramp:

- `url`: GETs of presigned URLs over plain HTTP, one new connection per download (`signed: true`; add
  `keepalive: true` to reuse connections). This is the client path of signed-URL downloads.
- `header`: header-signed GETs through warp, for comparison and as the ceiling of the gateways.

Each level reports Gbps and, in the record, P50 and P99 time to first byte, request rate and errors. Look for the
concurrency where Gbps stops growing, P99 climbs or errors appear; that is the knee for one client.

```bash
export IBENCH_S3_ENDPOINT=https://<gateway> IBENCH_S3_BUCKET=<bucket> AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
uv run ibench-storage mkdata rubin-access/single-user-burst --profile s3          # visit_image payloads, once
uv run ibench-storage run    rubin-access/single-user-burst --profile s3 --client <label> --cache warm --repeat 3
```

- Run it from each vantage point (`--client`) and node shape; label system state with `--tag` (for example
  `--tag nic_tier=on`) so before and after runs form separate series.
- Gateway scaling: repeat with one, then several comma-separated endpoints in `IBENCH_S3_ENDPOINT`; the endpoint list
  is part of the series.
- One Python process bounds the `url` step; if `url` and `header` agree at high concurrency, read the gateway
  ceiling from `header`.
- Presigned URLs are valid for the step duration plus a minute (at least 15 minutes); `expires_s` overrides.
