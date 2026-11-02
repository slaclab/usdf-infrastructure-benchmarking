# rubin-access/gateway-failover

A steady read load for five minutes while an operator removes one gateway from the pool and puts it back. The record
keeps a one-second timeline so the dip, the errors and the recovery are visible, not averaged away.

```bash
export IBENCH_S3_ENDPOINT=https://<production hostname> IBENCH_S3_BUCKET=<bucket> AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
uv run ibench-storage run rubin-access/gateway-failover --profile s3 --client <label> --tag event=baseline
# again, and remove one gateway at about 100 s and restore it at about 200 s
uv run ibench-storage run rubin-access/gateway-failover --profile s3 --client <label> --tag event=one-gateway-down
```

Use the hostname clients use, so the result shows what clients see; a per-node endpoint tests that node only (its
name must be in the certificate). Compare the two records:

```bash
jq '.metrics | {gbps, min_1s_gbps, median_1s_gbps, errors, timeline_gbps, timeline_errors}' storage/results/<record>.json
```

`min_1s_gbps` over `median_1s_gbps` is the depth of the dip; `timeline_errors` shows when clients saw failures. A
failed download is retried after a short pause by the next iteration, so errors measure what a client sees, not what
the pool lost. Note the removal and restore times in the run's `--tag`s or in the factsheet.
