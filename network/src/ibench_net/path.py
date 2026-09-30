"""Latency and path MTU via ping and tracepath."""
from __future__ import annotations

import re
import socket
import statistics
import time

from ibench.env import sh


def parse_ping(text: str) -> dict:
    rtt = re.search(r"= ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms", text)
    loss = re.search(r"([\d.]+)% packet loss", text)
    mn, avg, mx, mdev = (float(x) for x in rtt.groups()) if rtt else (None,) * 4
    return {"rtt_min_ms": mn, "rtt_avg_ms": avg, "rtt_max_ms": mx, "rtt_mdev_ms": mdev,
            "loss_pct": float(loss[1]) if loss else None}


def parse_tracepath(text: str) -> dict:
    pmtu = re.findall(r"pmtu (\d+)", text)
    hops = re.findall(r"^\s*(\d+)\??:", text, re.M)
    return {"pmtu": int(pmtu[-1]) if pmtu else None, "hops": int(hops[-1]) if hops else None}


def tcp_rtt(host: str, port: int, count: int) -> dict:
    """Connect-time RTT for hosts that drop ICMP."""
    rtt = []
    for _ in range(count):
        t = time.perf_counter()
        try:
            socket.create_connection((host, port), timeout=5).close()
        except OSError:
            continue
        rtt.append((time.perf_counter() - t) * 1000)
    if not rtt:
        raise SystemExit(f"cannot reach {host}:{port}")
    return {"rtt_min_ms": min(rtt), "rtt_avg_ms": statistics.fmean(rtt), "rtt_max_ms": max(rtt),
            "rtt_mdev_ms": statistics.pstdev(rtt), "loss_pct": 100 * (1 - len(rtt) / count)}


def probe(host: str, count: int = 20, port: int = 443) -> dict:
    """ICMP RTT and loss when ping works, else TCP connect time to `port`; PMTU and hops when tracepath exists."""
    ping = parse_ping(sh("ping", "-c", str(count), "-q", host, timeout=count * 2 + 10) or "")
    method = "icmp" if ping["rtt_avg_ms"] is not None else "tcp-connect"
    trace = sh("tracepath", "-n", host, timeout=60) or ""
    rtt = ping if method == "icmp" else tcp_rtt(host, port, count)
    return {**rtt, **parse_tracepath(trace), "method": method, "tracepath": trace}
