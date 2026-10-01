"""warp (github.com/minio/warp) GET runs over objects that already exist: command, credentials, result parsing."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

import zstandard

from ibench_storage.engine import Job

BIN = os.environ.get("WARP_BIN", "warp")


def hosts(endpoint: str) -> tuple[str, bool]:
    """Comma-separated endpoint URLs -> warp --host value and whether to use TLS."""
    urls = [urlparse(e.strip() if "//" in e else f"//{e.strip()}") for e in endpoint.split(",")]
    tls = {u.scheme == "https" for u in urls}
    if len(tls) > 1:
        raise SystemExit("endpoints mix http and https")
    return ",".join(u.netloc for u in urls), tls.pop()


def _env() -> dict:
    key, secret = os.environ.get("AWS_ACCESS_KEY_ID"), os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not (key and secret):
        raise SystemExit("set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
    env = {**os.environ, "WARP_ACCESS_KEY": key, "WARP_SECRET_KEY": secret}
    if token := os.environ.get("AWS_SESSION_TOKEN"):
        env["WARP_SESSION_TOKEN"] = token
    return env


def job(prof: dict, prefix: str, concurrency: int, duration_s: float, range_bytes: int, base: Path) -> Job:
    """Read-only by construction: --list-existing uses what is there, --noclear never deletes from the bucket
    (warp otherwise empties its bucket). Credentials travel in the environment, not on the command line."""
    host, tls = hosts(prof["endpoint"])
    cmd = [BIN, "get", "--no-color", "--host", host, "--bucket", prof["bucket"], "--prefix", prefix,
           "--lookup", prof.get("lookup") or "path", "--host-select", "roundrobin", "--list-existing", "--noclear",
           "--concurrent", str(concurrency), "--duration", f"{int(duration_s)}s", "--benchdata", str(base)]
    if tls:
        cmd.append("--tls")
    if prof.get("region"):
        cmd += ["--region", prof["region"]]
    if range_bytes:
        cmd += ["--range", "--range-size", str(range_bytes)]
    return Job("warp", cmd, _env(), Path(f"{base}.json.zst"), parse)


def _latency(op: dict) -> dict:
    """Request-weighted median and worst-bucket P99 of time to first byte over every size class warp reports."""
    buckets = []
    for segments in op["requests_by_client"].values():
        for seg in segments:
            if s := seg.get("single_sized_requests"):
                buckets.append({"n": s["requests"], "bytes": s["obj_size"], "ttfb": s["first_byte"],
                                "avg": s["dur_avg_millis"], "p99": s["dur_99_millis"]})
            for b in (seg.get("multi_sized_requests") or {}).get("by_size", []):
                buckets.append({"n": b["requests"], "bytes": b["avg_obj_size"], "ttfb": b["first_byte"],
                                "avg": b["avg_duration_millis"], "p99": None})
    n = sum(b["n"] for b in buckets) or 1
    out = {"p50_ms": sum(b["n"] * b["ttfb"]["median_millis"] for b in buckets) / n,
           "p99_ms": max(b["ttfb"]["p99_millis"] for b in buckets),
           "req_avg_ms": sum(b["n"] * b["avg"] for b in buckets) / n, "latency_basis": "ttfb"}
    if all(b["p99"] is not None for b in buckets):
        out["req_p99_ms"] = max(b["p99"] for b in buckets)
    return out


def parse(path: Path) -> dict:
    with path.open("rb") as f:
        data = json.loads(zstandard.ZstdDecompressor().stream_reader(f).read())
    op = data["by_op_type"].get("GET")
    if not op:
        raise SystemExit("warp recorded too few samples; raise duration_s or concurrency")
    t = op["throughput"]
    secs = t["measure_duration_millis"] / 1000
    requests, errors = op["total_requests"], op["total_errors"]
    if not requests or errors >= requests:
        raise SystemExit(f"warp GET failed: {errors} errors in {requests} requests; first: {op.get('first_errors')}")
    return {"gbps": t["bytes"] * 8 / secs / 1e9, "mbps": t["bytes"] / secs / 1e6, "objects_per_s": t["objects"] / secs,
            "requests": requests, "errors": errors, "measure_s": secs, "hosts": op["hosts"], **_latency(op),
            "raw": str(path)}
