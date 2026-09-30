from __future__ import annotations

import argparse

from ibench.cli import add_common, finish
from ibench_storage import mix, mlperf, profiles, scenario
from ibench_storage.steps import micro_run


def _levels(s: str) -> list[int]:
    return [int(x) for x in s.split(",")]


def cmd_micro(a: argparse.Namespace) -> None:
    prof = profiles.load(a.profile, bucket=a.bucket)
    keys = ("key", "prefix", "levels", "iterations", "chunk_mib", "n", "size", "concurrency",
            "max_objects", "max_gb", "label", "duration_s")
    args = {k: getattr(a, k) for k in keys if getattr(a, k, None) is not None}
    if a.no_warmup:
        args["warmup"] = False
    finish(micro_run(a.test, profiles.backend(prof), prof, args, a.scenario), a, "storage")


def cmd_mlperf(a: argparse.Namespace) -> None:
    scn = scenario.load(a.scenario)
    m = scn["mlperf"]
    prof = profiles.load(a.profile)
    factor = a.mem_factor or m["mem_factor"]
    if a.action == "datagen":
        mlperf.datagen(a.scenario, m, prof, a.run, factor, a.procs)
    elif a.action == "configview":
        mlperf.configview(a.scenario, m, prof, a.run, factor)
    else:
        for r in mlperf.run(a.scenario, m, prof, a.run, factor):
            finish(r, a, "storage")


def cmd_run(a: argparse.Namespace) -> None:
    """Run every micro step of a scenario (MLPerf steps are run explicitly: they need datagen first)."""
    scn = scenario.load(a.scenario)
    prof = profiles.load(a.profile)
    be = profiles.backend(prof)
    for step in scn.get("micro", []):
        step = dict(step)
        finish(micro_run(step.pop("test"), be, prof, step, a.scenario), a, "storage")


def cmd_mix(a: argparse.Namespace) -> None:
    """Run the scenario's loads alone and together; the ratio records are the interference."""
    prof = profiles.load(a.profile)
    for r in mix.run(prof, scenario.load(a.scenario)["mix"], a.scenario, a.only, a.start_at):
        finish(r, a, "storage")


def main() -> None:
    p = argparse.ArgumentParser(prog="ibench-storage", description="Storage benchmarks: micro and MLPerf.")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("micro", help="ad-hoc microbenchmark")
    m.add_argument("test", choices=("throughput", "latency", "bulk"))
    m.add_argument("--profile", required=True)
    m.add_argument("--bucket", help="override the profile bucket")
    m.add_argument("--scenario", default="")
    m.add_argument("--label", help="suffix to tell apart steps of the same test")
    m.add_argument("--key")
    m.add_argument("--prefix")
    m.add_argument("--levels", type=_levels)
    m.add_argument("--iterations", type=int)
    m.add_argument("--chunk-mib", dest="chunk_mib", type=int)
    m.add_argument("--no-warmup", action="store_true")
    m.add_argument("-n", type=int, help="latency: number of reads (use >=1000 for a meaningful P99)")
    m.add_argument("--size", type=int, help="latency: bytes per read")
    m.add_argument("--concurrency", type=int)
    m.add_argument("--duration", dest="duration_s", type=float, help="latency/bulk: run for this many seconds")
    m.add_argument("--max-objects", dest="max_objects", type=int)
    m.add_argument("--max-gb", dest="max_gb", type=float)
    m.set_defaults(fn=cmd_micro)

    k = sub.add_parser("mlperf", help="MLPerf Storage scenario: datagen, configview, run")
    k.add_argument("action", choices=("datagen", "configview", "run"))
    k.add_argument("scenario")
    k.add_argument("--profile", required=True)
    k.add_argument("--run", help="only this run (datagen: only the datasets it needs)")
    k.add_argument("--mem-factor", dest="mem_factor", type=float, help="dataset size as a multiple of client RAM")
    k.add_argument("--procs", type=int, default=16, help="datagen processes")
    k.set_defaults(fn=cmd_mlperf)

    r = sub.add_parser("run", help="run all micro steps of a scenario")
    r.add_argument("scenario")
    r.add_argument("--profile", required=True)
    r.set_defaults(fn=cmd_run)

    x = sub.add_parser("mix", help="run a scenario's loads alone and together, report the interference")
    x.add_argument("scenario")
    x.add_argument("--profile", required=True)
    x.add_argument("--only", help="run one load only (for loads split across hosts)")
    x.add_argument("--start-at", dest="start_at", type=float, help="unix time to start at; with --only marks the phase 'together'")
    x.set_defaults(fn=cmd_mix)

    for s in (m, k, r, x):
        add_common(s)
    a = p.parse_args()
    a.fn(a)
