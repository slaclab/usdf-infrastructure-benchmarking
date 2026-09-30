"""iperf3 client wrapper; the server side is started by the operator (`iperf3 -s -p PORT`)."""
from __future__ import annotations

import json
import subprocess


def parse(out: dict) -> dict:
    end = out["end"]
    cpu = end.get("cpu_utilization_percent", {})
    return {
        "gbps": end["sum_received"]["bits_per_second"] / 1e9,
        "gbps_sent": end["sum_sent"]["bits_per_second"] / 1e9,
        "retransmits": end["sum_sent"].get("retransmits"),
        "cpu_client_pct": cpu.get("host_total"),
        "cpu_server_pct": cpu.get("remote_total"),
        "congestion": end.get("sender_tcp_congestion"),
    }


def run(host: str, port: int, streams: int, seconds: int, reverse: bool, omit: int) -> dict:
    cmd = ["iperf3", "-c", host, "-p", str(port), "-P", str(streams), "-t", str(seconds), "-O", str(omit), "-J"]
    if reverse:
        cmd.append("-R")
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(r.stderr.strip() or "iperf3 returned no JSON") from None
    if "error" in out:
        raise RuntimeError(out["error"])
    return parse(out)
