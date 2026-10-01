"""Read the result of an iperf3 run made elsewhere: `-J` JSON or the plain-text report."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

FACTOR = {"": 1, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}
RECEIVER = re.compile(r"^\[\s*(\w+)\]\s+[\d.]+-[\d.]+\s+sec\s+[\d.]+\s+\w+Bytes\s+([\d.]+)\s+([KMGT]?)bits/sec\s+receiver",
                      re.M)


def _json(out: dict) -> dict:
    start, end = out["start"], out["end"]
    ts = start.get("timestamp", {}).get("timesecs")
    return {"gbps": end["sum_received"]["bits_per_second"] / 1e9, "streams": start["test_start"]["num_streams"],
            "seconds": start["test_start"]["duration"], "reverse": bool(start["test_start"]["reverse"]),
            "retransmits": end["sum_sent"].get("retransmits"), "host": start.get("connecting_to", {}).get("host"),
            "started": datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds") if ts else None,
            "version": start.get("version")}


def _text(text: str) -> dict:
    rows = RECEIVER.findall(text)
    if not rows:
        raise ValueError("no iperf3 receiver line found")
    by_id = {i: float(v) * FACTOR[u] / 1e9 for i, v, u in rows}
    streams = [k for k in by_id if k != "SUM"]
    gbps = by_id["SUM"] if "SUM" in by_id else sum(by_id.values())
    return {"gbps": gbps, "streams": len(streams), "seconds": None, "reverse": None, "retransmits": None,
            "host": None, "started": None, "version": None}


def parse_file(path: Path) -> dict:
    text = path.read_text()
    try:
        out = json.loads(text)
    except json.JSONDecodeError:
        return _text(text)
    if "error" in out:
        raise ValueError(out["error"])
    return _json(out)
