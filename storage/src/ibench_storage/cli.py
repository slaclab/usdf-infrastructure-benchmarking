from __future__ import annotations

import argparse

from ibench.cli import add_common, add_repeat, repeat
from ibench_storage import data, mix, mlperf, profiles, scenario, steps, tokens
from ibench_storage.store import Store


def _levels(s: str) -> list[int]:
    return [int(x) for x in s.split(",")]


def _scenario(a: argparse.Namespace, key: str) -> dict:
    scn = scenario.load(a.scenario)
    if key not in scn:
        raise SystemExit(f"scenario {a.scenario!r} has no {key!r} section; it defines: "
                         f"{', '.join(k for k in scn if k != 'description')}")
    return scn


def cmd_run(a: argparse.Namespace) -> None:
    """Every read step of a scenario; MLPerf, mix and tokenize scenarios have their own commands."""
    prof, base = profiles.load(a.profile), scenario.base_prefix()
    repeat(a, "storage", lambda: [r for s in _scenario(a, "steps")["steps"] for r in steps.run(prof, s, a.scenario, base)])


def cmd_get(a: argparse.Namespace) -> None:
    """Ad-hoc read step against any prefix (for example existing data)."""
    prof = profiles.load(a.profile, bucket=a.bucket)
    step = {k: v for k, v in {"label": a.label, "prefix": a.prefix, "concurrency": a.concurrency,
                              "duration_s": a.duration, "range_kib": a.range_kib, "metric": a.metric,
                              "max_objects": a.max_objects, "direct": a.direct or None, "signed": a.signed or None,
                              "keepalive": a.keepalive or None}.items() if v is not None}
    repeat(a, "storage", lambda: steps.run(prof, step, a.scenario, ""))


def cmd_mix(a: argparse.Namespace) -> None:
    """Loads alone and together; the ratio records are the interference."""
    prof, base = profiles.load(a.profile), scenario.base_prefix()
    loads = _scenario(a, "mix")["mix"]
    repeat(a, "storage", lambda: mix.run(prof, loads, a.scenario, base, a.only, a.start_at))


def cmd_tokens(a: argparse.Namespace) -> None:
    prof, base = profiles.load(a.profile), scenario.base_prefix()
    spec = _scenario(a, "tokenize")["tokenize"]
    repeat(a, "storage", lambda: [tokens.run(prof, spec, a.scenario, base, a.workers, a.keep_output)])


def cmd_mkdata(a: argparse.Namespace) -> None:
    names = a.classes or (scenario.data_classes(scenario.load(a.scenario)) if a.scenario else [])
    if not names:
        raise SystemExit("no data classes: name a scenario that reads mock data or pass --classes")
    data.generate(Store(profiles.load(a.profile)), scenario.base_prefix(), names, a.scale, a.workers, a.max_gb,
                  a.dry_run)


def cmd_mlperf(a: argparse.Namespace) -> None:
    m = _scenario(a, "mlperf")["mlperf"]
    prof = profiles.load(a.profile)
    factor = a.mem_factor or m["mem_factor"]
    if a.action == "datagen":
        mlperf.datagen(a.scenario, m, prof, a.run, factor, a.procs)
    elif a.action == "configview":
        mlperf.configview(a.scenario, m, prof, a.run, factor)
    else:
        repeat(a, "storage", lambda: mlperf.run(a.scenario, m, prof, a.run, factor))


def main() -> None:
    p = argparse.ArgumentParser(prog="ibench-storage", description="Storage benchmarks: reads, interference, MLPerf.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def scenario_cmd(name: str, fn, help: str) -> argparse.ArgumentParser:
        c = sub.add_parser(name, help=help)
        c.add_argument("scenario", help=f"one of: {', '.join(scenario.names())}")
        c.add_argument("--profile", required=True)
        c.set_defaults(fn=fn)
        return c

    r = scenario_cmd("run", cmd_run, "run the read steps of a scenario")
    add_repeat(r)

    g = sub.add_parser("get", help="ad-hoc read step: warp for S3 profiles, fio for POSIX")
    g.add_argument("--profile", required=True)
    g.add_argument("--bucket", help="override the profile bucket")
    g.add_argument("--prefix", required=True, help="key prefix (S3) or directory relative to the root (POSIX)")
    g.add_argument("--label", default="adhoc")
    g.add_argument("--concurrency", type=_levels, default=[8], help="one value, or a list to sweep: 1,8,32")
    g.add_argument("--duration", type=float, default=60, help="seconds per level")
    g.add_argument("--range-kib", dest="range_kib", type=float, help="random ranged reads of this size; default whole objects")
    g.add_argument("--metric", choices=("throughput", "latency"), default="throughput")
    g.add_argument("--max-objects", dest="max_objects", type=int)
    g.add_argument("--direct", action="store_true", help="POSIX: O_DIRECT reads")
    g.add_argument("--signed", action="store_true", help="S3: GET presigned URLs over plain HTTP instead of using warp")
    g.add_argument("--keepalive", action="store_true", help="with --signed: reuse connections (default: one per download)")
    g.set_defaults(fn=cmd_get, scenario="adhoc")
    add_repeat(g)

    x = scenario_cmd("mix", cmd_mix, "run a scenario's loads alone and together, report the interference")
    x.add_argument("--only", help="run one load only (for loads split across hosts)")
    x.add_argument("--start-at", dest="start_at", type=float,
                   help="unix time to start at; with --only marks the phase 'together'")
    add_repeat(x)

    t = scenario_cmd("tokens", cmd_tokens, "tokenization workload: read text shards, write token shards")
    t.add_argument("--workers", type=int, help="processes (default: the scenario's, else all CPUs)")
    t.add_argument("--keep-output", dest="keep_output", action="store_true")
    add_repeat(t)

    d = sub.add_parser("mkdata", help="write mock payloads (datasets.yaml) under IBENCH_DATA_PREFIX")
    d.add_argument("scenario", nargs="?", help="write the classes this scenario reads")
    d.add_argument("--classes", type=lambda s: s.split(","), help="comma-separated classes instead of a scenario")
    d.add_argument("--profile", required=True)
    d.add_argument("--scale", type=float, default=1.0, help="multiply object counts (use 0.05 for a smoke test)")
    d.add_argument("--workers", type=int, default=8)
    d.add_argument("--max-gb", dest="max_gb", type=float, default=200, help="refuse to write more than this")
    d.add_argument("--dry-run", dest="dry_run", action="store_true", help="print the size and stop")
    d.set_defaults(fn=cmd_mkdata)

    k = sub.add_parser("mlperf", help="MLPerf Storage scenario: datagen, configview, run")
    k.add_argument("action", choices=("datagen", "configview", "run"))
    k.add_argument("scenario", help=f"one of: {', '.join(scenario.names())}")
    k.add_argument("--profile", required=True)
    k.set_defaults(fn=cmd_mlperf)
    k.add_argument("--run", help="only this run (datagen: only the datasets it needs)")
    k.add_argument("--mem-factor", dest="mem_factor", type=float, help="dataset size as a multiple of client RAM")
    k.add_argument("--procs", type=int, default=16, help="datagen processes")
    add_repeat(k)

    for s in (r, g, x, t, k):
        add_common(s)
    a = p.parse_args()
    a.fn(a)
