"""GETs over presigned URLs of objects that already exist: the client side of signed-URL downloads.

A presigned URL carries its own authorisation, so a plain HTTP client can fetch it; by default every download opens a
new connection, as a browser or a one-off script does. Runs as `python -m ibench_storage.signedurl` so it fits the same
Job/parse flow as warp. One Python process bounds the throughput; use warp to find the gateway ceiling.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import boto3
import urllib3
from botocore.config import Config

from ibench_storage.engine import Job

CHUNK = 1 << 20
BACKOFF_S = 0.1  # pause after a failed download, so a dead endpoint does not spin the client


def job(prof: dict, prefix: str, concurrency: int, duration_s: float, range_bytes: int, base: Path,
        keepalive: bool = False, expires_s: int | None = None, max_objects: int = 500) -> Job:
    """Credentials travel in the environment; URLs are signed inside the subprocess and never printed."""
    if not (os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY")):
        raise SystemExit("set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
    out = Path(f"{base}.json")
    cmd = [sys.executable, "-m", "ibench_storage.signedurl", "--endpoint", prof["endpoint"], "--bucket", prof["bucket"],
           "--prefix", prefix, "--lookup", prof.get("lookup") or "path", "--concurrency", str(concurrency),
           "--duration", str(int(duration_s)), "--range-bytes", str(range_bytes),
           "--expires", str(expires_s or max(900, int(duration_s) + 60)), "--max-objects", str(max_objects),
           "--region", prof.get("region") or "us-east-1", "--out", str(out)]
    if keepalive:
        cmd.append("--keepalive")
    return Job("signed-url", cmd, dict(os.environ), out, parse)


def _http(url: str, concurrency: int) -> urllib3.PoolManager:
    """Honours HTTPS_PROXY / NO_PROXY like warp does."""
    u = urlparse(url)
    kw = {"maxsize": concurrency, "retries": False, "timeout": urllib3.Timeout(connect=10, read=60)}
    proxy = urllib.request.getproxies().get(u.scheme)
    if proxy and not urllib.request.proxy_bypass(u.hostname):
        return urllib3.ProxyManager(proxy, **kw)
    return urllib3.PoolManager(**kw)


def _worker(http, links, sizes, range_bytes, keepalive, t0, deadline, secs, idx) -> dict:
    """Download random objects until the deadline. Bytes are counted per second as they arrive; a download cut off by
    the deadline counts its bytes but not its latency."""
    rng = random.Random(idx)
    out = {"ttfb": [], "dur": [], "objects": 0, "errors": 0, "first_error": "", "bytes": [0] * secs, "err": [0] * secs}
    n = idx
    while time.monotonic() < deadline:
        j = rng.randrange(len(links))
        url = links[j][n % len(links[j])]
        n += 1
        headers = {} if keepalive else {"Connection": "close"}
        if range_bytes:
            start = rng.randrange(max(1, sizes[j] - range_bytes + 1))
            headers["Range"] = f"bytes={start}-{start + range_bytes - 1}"
        t, first, whole, r = time.monotonic(), None, True, None
        try:
            r = http.request("GET", url, headers=headers, preload_content=False)
            if r.status >= 400:
                raise OSError(f"HTTP {r.status}")
            for chunk in r.stream(CHUNK):
                now = time.monotonic()
                first = now - t if first is None else first
                if now >= deadline:
                    whole = False
                    break
                out["bytes"][min(int(now - t0), secs - 1)] += len(chunk)
            if whole:
                end = time.monotonic()
                out["ttfb"].append(end - t if first is None else first)
                out["dur"].append(end - t)
                out["objects"] += 1
                r.release_conn()
            else:
                r.close()
        except Exception as e:  # noqa: BLE001 - every failure is a counted error, not a crash
            if r is not None:
                r.close()
            out["errors"] += 1
            out["err"][min(int(time.monotonic() - t0), secs - 1)] += 1
            out["first_error"] = out["first_error"] or f"{type(e).__name__}: {e}"
            time.sleep(BACKOFF_S)
    return out


def _pct(xs: list[float], p: float) -> float:
    return xs[max(0, math.ceil(p * len(xs)) - 1)] if xs else 0.0


def summarise(parts: list[dict], duration: float, hosts: int) -> dict:
    """Same keys as warp.parse, plus a per-second timeline for watching a gateway disappear and return."""
    secs = max(1, math.ceil(duration))
    by_sec = [sum(p["bytes"][i] for p in parts) for i in range(secs)]
    errs = [sum(p["err"][i] for p in parts) for i in range(secs)]
    total, objects, errors = sum(by_sec), sum(p["objects"] for p in parts), sum(p["errors"] for p in parts)
    ttfb, dur = sorted(x for p in parts for x in p["ttfb"]), sorted(x for p in parts for x in p["dur"])
    gbps = [b * 8 / 1e9 for b in by_sec]
    full = gbps[:int(duration)] or gbps
    return {"gbps": total * 8 / duration / 1e9, "mbps": total / duration / 1e6, "objects_per_s": objects / duration,
            "requests": objects + errors, "errors": errors, "measure_s": duration, "hosts": hosts,
            "p50_ms": _pct(ttfb, 0.5) * 1e3, "p99_ms": _pct(ttfb, 0.99) * 1e3,
            "req_avg_ms": sum(dur) / len(dur) * 1e3 if dur else 0.0, "req_p99_ms": _pct(dur, 0.99) * 1e3,
            "latency_basis": "ttfb", "min_1s_gbps": min(full), "median_1s_gbps": statistics.median(full),
            "timeline_gbps": [round(g, 4) for g in gbps], "timeline_errors": errs,
            "first_error": next((p["first_error"] for p in parts if p["first_error"]), "")}


def parse(path: Path) -> dict:
    m = json.loads(path.read_text())
    if not m["requests"] or m["errors"] >= m["requests"]:
        raise SystemExit(f"signed-URL GET failed: {m['errors']} errors in {m['requests']} requests; "
                         f"first: {m['first_error']}")
    return {**m, "raw": str(path)}


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m ibench_storage.signedurl")
    p.add_argument("--endpoint", required=True, help="comma-separated endpoint URLs; downloads rotate over them")
    p.add_argument("--bucket", required=True)
    p.add_argument("--prefix", required=True)
    p.add_argument("--lookup", default="path")
    p.add_argument("--region", default="us-east-1")
    p.add_argument("--concurrency", type=int, required=True)
    p.add_argument("--duration", type=int, required=True)
    p.add_argument("--range-bytes", dest="range_bytes", type=int, default=0)
    p.add_argument("--expires", type=int, default=900, help="URL lifetime in seconds")
    p.add_argument("--max-objects", dest="max_objects", type=int, default=500)
    p.add_argument("--keepalive", action="store_true", help="reuse connections instead of one per download")
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)

    cfg = Config(signature_version="s3v4", s3={"addressing_style": "virtual" if a.lookup == "host" else "path"})
    clients = [boto3.client("s3", endpoint_url=e.strip(), region_name=a.region, config=cfg)
               for e in a.endpoint.split(",")]
    listed: list[tuple[str, int]] = []
    for page in clients[0].get_paginator("list_objects_v2").paginate(Bucket=a.bucket, Prefix=a.prefix):
        listed += [(o["Key"], o["Size"]) for o in page.get("Contents", [])]
        if len(listed) >= a.max_objects:
            break
    listed = listed[:a.max_objects]
    if not listed:
        raise SystemExit(f"nothing under {a.prefix!r}")
    links = [[c.generate_presigned_url("get_object", Params={"Bucket": a.bucket, "Key": k}, ExpiresIn=a.expires)
              for c in clients] for k, _ in listed]
    sizes = [s for _, s in listed]

    http = _http(links[0][0], a.concurrency)
    secs = max(1, math.ceil(a.duration))
    t0 = time.monotonic()
    with ThreadPoolExecutor(a.concurrency) as ex:
        parts = list(ex.map(lambda i: _worker(http, links, sizes, a.range_bytes, a.keepalive, t0, t0 + a.duration,
                                              secs, i), range(a.concurrency)))
    Path(a.out).write_text(json.dumps(summarise(parts, a.duration, len(clients))))


if __name__ == "__main__":
    main()
