from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

from ibench import Run, capture, metric
from ibench.cli import add_common, finish
from ibench_net import importer, iperf, path


def cmd_iperf(a: argparse.Namespace) -> None:
    for streams in (int(s) for s in a.streams.split(",")):
        t0 = time.time()
        m = iperf.run(a.host, a.port, streams, a.seconds, a.reverse, a.omit)
        params = {"host": a.host, "port": a.port, "streams": streams, "seconds": a.seconds,
                  "reverse": a.reverse, "omit": a.omit}
        run = Run("network", f"iperf3.p{streams}", metric("gbps", m["gbps"], "Gbps"), m, params,
                  scenario="from-server" if a.reverse else "to-server",
                  profile=a.profile or a.host, env=capture(), duration_s=time.time() - t0)
        a.tag = [*a.tag, f"scope={a.scope}"] if a.scope else a.tag
        finish(run, a, "network")


def cmd_import(a: argparse.Namespace) -> None:
    """Record iperf3 output from runs made elsewhere. Several files are parallel host pairs: results are summed."""
    parts = []
    for f in a.files:
        try:
            parts.append(importer.parse_file(f))
        except (ValueError, KeyError, OSError) as e:
            raise SystemExit(f"{f}: {e}") from None
    first, pairs = parts[0], len(parts)
    streams = first["streams"]
    reverse = a.reverse if a.reverse is not None else first["reverse"]
    if reverse is None:
        raise SystemExit("direction unknown from a text report: pass --reverse or --to-server")
    total = sum(p["gbps"] for p in parts)
    name = f"iperf3.p{streams}" + (f".x{pairs}" if pairs > 1 else "")
    started = a.date or first["started"] or datetime.fromtimestamp(a.files[0].stat().st_mtime, timezone.utc).isoformat(
        timespec="seconds")
    params = {"streams": streams, "pairs": pairs, "seconds": first["seconds"], "imported": [f.name for f in a.files]}
    metrics = {"gbps": total}
    if pairs > 1:
        metrics |= {f"gbps_pair{i + 1}": p["gbps"] for i, p in enumerate(parts)}
    run = Run("network", name, metric("gbps", total, "Gbps"), metrics, params,
              scenario="from-server" if reverse else "to-server", profile=a.profile or first["host"] or "unknown",
              started=started, source=a.source or "imported iperf3 output")
    a.tag = [*a.tag, f"scope={a.scope}"]
    finish(run, a, "network")


def cmd_path(a: argparse.Namespace) -> None:
    t0 = time.time()
    m = path.probe(a.host, a.count, a.port)
    run = Run("network", "path", metric("rtt_avg_ms", m["rtt_avg_ms"] or float("nan"), "ms", False), m,
              {"host": a.host, "count": a.count, "port": a.port}, profile=a.profile or a.host, env=capture(),
              duration_s=time.time() - t0)
    finish(run, a, "network")


def main() -> None:
    p = argparse.ArgumentParser(prog="ibench-net", description="Network benchmarks: iperf3 and path probes.")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("iperf", help="iperf3 client; sweep streams with --streams 1,8,16")
    i.add_argument("host")
    i.add_argument("--port", type=int, default=5201)
    i.add_argument("--streams", default="8")
    i.add_argument("--seconds", type=int, default=30)
    i.add_argument("--omit", type=int, default=2, help="seconds excluded from the result (TCP ramp-up)")
    i.add_argument("-R", "--reverse", action="store_true", help="server sends")
    i.add_argument("--scope", choices=("wan", "internal"), help="wan: across the internet or a cloud; internal: within the site")
    i.set_defaults(fn=cmd_iperf)

    m = sub.add_parser("import", help="record iperf3 output (-J JSON or text) from a run made elsewhere")
    m.add_argument("files", nargs="+", type=Path, help="one file per host pair; results are summed")
    m.add_argument("--scope", required=True, choices=("wan", "internal"))
    m.add_argument("--profile", help="label for the target (default: host in the JSON)")
    m.add_argument("--date", help="ISO date or time of the run (default: from the file)")
    m.add_argument("--source", help="where the numbers come from (ticket, channel, document)")
    d = m.add_mutually_exclusive_group()
    d.add_argument("--reverse", dest="reverse", action="store_true", default=None, help="server sent (from-server)")
    d.add_argument("--to-server", dest="reverse", action="store_false", help="client sent (to-server)")
    m.set_defaults(fn=cmd_import)
    add_common(m)

    q = sub.add_parser("path", help="RTT/loss (ping, else TCP connect) and tracepath PMTU")
    q.add_argument("host")
    q.add_argument("--count", type=int, default=20)
    q.add_argument("--port", type=int, default=443, help="TCP port for the connect-time fallback when ICMP is blocked")
    q.set_defaults(fn=cmd_path)

    for s in (i, q):
        s.add_argument("--profile", help="label for the target (default: host)")
        add_common(s)
    a = p.parse_args()
    a.fn(a)
