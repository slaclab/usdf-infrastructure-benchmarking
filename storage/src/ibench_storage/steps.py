"""A read step -> one job per concurrency level -> Run records. S3 profiles use warp, POSIX profiles use fio."""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from ibench import Run, capture, metric
from ibench_storage import engine, fio, warp
from ibench_storage.profiles import target
from ibench_storage.store import Store

MIB = 1 << 20


@dataclass
class Planned:
    name: str
    level: int
    prefix: str
    job: engine.Job


def prefix_of(step: dict, base: str) -> str:
    return step["prefix"] if "prefix" in step else f"{base}/{step['data']}/"


def _range_bytes(step: dict) -> int:
    if "range_kib" in step:
        return int(step["range_kib"] * 1024)
    return int(step.get("range_mib", 0) * MIB)


def plan(prof: dict, step: dict, scenario: str, base: str) -> list[Planned]:
    """Jobs for one step; the listing check fails early on a missing prefix instead of mid-run."""
    prefix = prefix_of(step, base)
    store = Store(prof)
    found = store.list(prefix, limit=step.get("max_objects", 500))
    if not found:
        raise SystemExit(f"nothing under {prefix!r} on {target(prof)}; create it with `ibench-storage mkdata` "
                         "or point the step at existing data")
    levels = step["concurrency"] if isinstance(step.get("concurrency"), list) else [step.get("concurrency", 8)]
    rng = _range_bytes(step)
    out = []
    for level in levels:
        name = f"read.{step['label']}" + (f".c{level}" if len(levels) > 1 else "")
        base_path = engine.RAW / f"{int(time.time())}_{scenario.replace('/', '-')}_{name}"
        if prof["kind"] == "s3":
            job = warp.job(prof, prefix, level, step.get("duration_s", 60), rng, base_path)
        else:
            files = [str(Path(prof["root"]) / k) for k, _ in found]
            job = fio.job(files, level, step.get("duration_s", 60), rng or MIB, not rng, step.get("direct", False),
                          base_path)
        out.append(Planned(name, level, prefix, job))
    return out


def record(prof: dict, p: Planned, metrics: dict, step: dict, scenario: str, seconds: float) -> Run:
    primary = (metric("p99_ms", metrics["p99_ms"], "ms", higher_is_better=False)
               if step.get("metric") == "latency" else metric("gbps", metrics["gbps"], "Gbps"))
    env = {**capture(prof.get("root")),
           "tool": {"name": p.job.tool, "version": engine.version(p.job.cmd[0]), "cmd": p.job.cmd}}
    return Run("storage", p.name, primary, metrics, {**step, "prefix": p.prefix, "concurrency": p.level}, scenario,
               prof["name"], env=env, duration_s=seconds, tags={"target": target(prof)})


def run(prof: dict, step: dict, scenario: str, base: str) -> list[Run]:
    out = []
    for p in plan(prof, step, scenario, base):
        t0 = time.time()
        out.append(record(prof, p, engine.execute(p.job), step, scenario, time.time() - t0))
    return out
