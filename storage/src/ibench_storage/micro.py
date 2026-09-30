"""Backend-agnostic read microbenchmarks: throughput vs concurrency, latency percentiles, bulk transfer."""
from __future__ import annotations

import itertools
import math
import random
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from ibench_storage.backends import CHUNK


def pct(xs: list[float], q: float) -> float:
    s = sorted(xs)
    return s[max(0, math.ceil(q / 100 * len(s)) - 1)]


def _timed(fn, *args) -> tuple[int, float]:
    t = time.perf_counter()
    n = fn(*args)
    return n, time.perf_counter() - t


def throughput(be, key: str, levels: list[int], iterations: int = 3, chunk: int = CHUNK, warmup: bool = True) -> dict:
    """Read one object with parallel ranged reads at each concurrency level (MB = 1e6 bytes)."""
    size = be.size(key)
    spans = [(o, min(chunk, size - o)) for o in range(0, size, chunk)]
    out = {}
    for c in levels:
        with ThreadPoolExecutor(c) as ex:
            def once():
                n, t = _timed(lambda: sum(ex.map(lambda s: be.read(key, *s), spans)))
                return n / t / 1e6
            if warmup:
                once()
            mbps = [once() for _ in range(iterations)]
        ttfb = [_timed(be.read, key, 0, 1)[1] * 1000 for _ in range(iterations)]
        mean = statistics.fmean(mbps)
        out[c] = {"mbps_mean": mean, "mbps_min": min(mbps), "mbps_max": max(mbps),
                  "gbps_mean": mean * 8 / 1000, "ttfb_ms_mean": statistics.fmean(ttfb)}
    peak = max(out, key=lambda c: out[c]["gbps_mean"])
    return {"size_bytes": size, "peak_gbps": out[peak]["gbps_mean"], "peak_concurrency": peak, "levels": out}


def latency(be, files: list[tuple[str, int]], n: int, size: int, concurrency: int = 1,
            duration_s: float | None = None) -> dict:
    """Random reads of `size` bytes over `files` (n reads, or as many as fit in duration_s).
    One file measures the hot path, many files the cold path."""
    deadline = time.monotonic() + duration_s if duration_s else None

    def one(_):
        key, fsize = random.choice(files)
        length = min(size, fsize)
        return _timed(be.read, key, random.randrange(0, fsize - length + 1), length)[1] * 1000

    def worker():
        out = []
        while time.monotonic() < deadline:
            out.append(one(None))
        return out

    with ThreadPoolExecutor(concurrency) as ex:
        if deadline:
            lat = [x for f in [ex.submit(worker) for _ in range(concurrency)] for x in f.result()]
        else:
            lat = list(ex.map(one, range(n)))
    return {"n": len(lat), "files": len(files), "size_bytes": size, "concurrency": concurrency,
            "mean_ms": statistics.fmean(lat), "p50_ms": pct(lat, 50), "p95_ms": pct(lat, 95),
            "p99_ms": pct(lat, 99), "max_ms": max(lat)}


def select(be, prefix: str, max_objects: int, max_bytes: int) -> list[tuple[str, int]]:
    chosen, total = [], 0
    for key, size in be.list(prefix):
        if len(chosen) >= max_objects or total + size > max_bytes:
            break
        chosen.append((key, size))
        total += size
    if not chosen:
        raise SystemExit(f"no objects under {prefix!r} within limits")
    return chosen


def bulk(be, objects: list[tuple[str, int]], concurrency: int, duration_s: float | None = None) -> dict:
    """Read whole objects in parallel (once each, or cycling for duration_s); aggregate rate and per-object time."""
    deadline = time.monotonic() + duration_s if duration_s else None
    todo = itertools.cycle(objects) if deadline else iter(objects)
    lock = threading.Lock()

    def worker():
        out = []
        while True:
            with lock:
                o = next(todo, None)
            if o is None or (deadline and time.monotonic() >= deadline):
                return out
            out.append(_timed(be.read, o[0], 0, o[1]))

    t0 = time.perf_counter()
    with ThreadPoolExecutor(concurrency) as ex:
        res = [r for f in [ex.submit(worker) for _ in range(concurrency)] for r in f.result()]
    wall = time.perf_counter() - t0
    total = sum(n for n, _ in res)
    per = [t for _, t in res]
    return {"objects": len(res), "bytes": total, "wall_s": wall, "concurrency": concurrency,
            "gbps": total * 8 / wall / 1e9, "objects_per_s": len(res) / wall,
            "obj_p50_s": pct(per, 50), "obj_p99_s": pct(per, 99)}
