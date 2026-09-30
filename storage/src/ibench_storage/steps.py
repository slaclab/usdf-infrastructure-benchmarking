"""Run one microbenchmark step and wrap it as a Run record."""
from __future__ import annotations

import time

from ibench import Run, capture, metric
from ibench_storage import micro


def micro_run(test: str, be, prof: dict, a: dict, scenario: str = "") -> Run:
    t0 = time.time()
    if test == "throughput":
        m = micro.throughput(be, a["key"], a.get("levels", [1, 4, 16, 32, 64]), a.get("iterations", 3),
                             a.get("chunk_mib", 8) << 20, a.get("warmup", True))
        primary = metric("peak_gbps", m["peak_gbps"], "Gbps")
    elif test == "latency":
        files = ([(a["key"], be.size(a["key"]))] if "key" in a else
                 micro.select(be, a["prefix"], a.get("max_objects", 1000), int(a.get("max_gb", 50) * 1e9)))
        m = micro.latency(be, files, a.get("n", 1000), a.get("size", 1 << 20), a.get("concurrency", 1),
                          a.get("duration_s"))
        primary = metric("p99_ms", m["p99_ms"], "ms", higher_is_better=False)
    elif test == "bulk":
        objects = micro.select(be, a["prefix"], a.get("max_objects", 1000), int(a.get("max_gb", 50) * 1e9))
        m = micro.bulk(be, objects, a.get("concurrency", 32), a.get("duration_s"))
        primary = metric("gbps", m["gbps"], "Gbps")
    else:
        raise SystemExit(f"unknown micro test {test!r}")
    name = f"micro.{test}" + (f".{a['label']}" if a.get("label") else "")
    where = prof.get("root") or f"{prof.get('endpoint')}/{prof.get('bucket')}"  # endpoint list => distinct series
    return Run("storage", name, primary, m, dict(a), scenario, prof["name"],
               env=capture(prof.get("root")), duration_s=time.time() - t0, tags={"target": where})
