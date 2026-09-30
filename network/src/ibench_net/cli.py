from __future__ import annotations

import argparse
import time

from ibench import Run, capture, metric
from ibench.cli import add_common, finish
from ibench_net import iperf, path


def cmd_iperf(a: argparse.Namespace) -> None:
    for streams in (int(s) for s in a.streams.split(",")):
        t0 = time.time()
        m = iperf.run(a.host, a.port, streams, a.seconds, a.reverse, a.omit)
        params = {"host": a.host, "port": a.port, "streams": streams, "seconds": a.seconds,
                  "reverse": a.reverse, "omit": a.omit}
        run = Run("network", "iperf3", metric("gbps", m["gbps"], "Gbps"), m, params,
                  scenario="from-server" if a.reverse else "to-server",
                  profile=a.profile or a.host, env=capture(), duration_s=time.time() - t0)
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
    i.set_defaults(fn=cmd_iperf)

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
