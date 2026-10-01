"""Hand-entered results: reports/intake/<suite>.csv rows become the same records the tools write."""
from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

REQUIRED = ("date", "source", "scope", "client", "target", "direction", "value")
SCOPES = ("wan", "internal")
DIRECTIONS = ("to-server", "from-server")
GBPS = {"gbps": 1, "mbps": 1e-3, "gb/s": 8, "mb/s": 8e-3, "gib/s": 8 * 1.073741824, "mib/s": 8 * 1.048576e-3}


def _fail(file: Path, line: int, msg: str):
    raise SystemExit(f"{file.name} line {line}: {msg}")


def _row(file: Path, line: int, r: dict) -> dict:
    r = {k: (v or "").strip() for k, v in r.items() if k}
    if missing := [k for k in REQUIRED if not r.get(k)]:
        _fail(file, line, f"missing {', '.join(missing)}")
    if r["scope"].lower() not in SCOPES:
        _fail(file, line, f"scope {r['scope']!r} must be one of {', '.join(SCOPES)}")
    if r["direction"].lower() not in DIRECTIONS:
        _fail(file, line, f"direction {r['direction']!r} must be one of {', '.join(DIRECTIONS)}")
    try:
        day = date.fromisoformat(r["date"])
    except ValueError:
        _fail(file, line, f"date {r['date']!r} must be YYYY-MM-DD")
    unit = (r.get("unit") or "Gbps").lower()
    if unit not in GBPS:
        _fail(file, line, f"unit {r['unit']!r} must be one of Gbps, Mbps, GB/s, MB/s, GiB/s, MiB/s")
    try:
        value = float(r["value"].replace(",", "")) * GBPS[unit]
    except ValueError:
        _fail(file, line, f"value {r['value']!r} is not a number")
    streams, pairs = r.get("streams", ""), r.get("pairs", "")
    tool = (r.get("tool") or "iperf3").lower()
    name = tool + (f".p{streams}" if streams else "") + (f".x{pairs}" if pairs not in ("", "1") else "")
    return {"suite": file.stem, "name": name, "scenario": r["direction"].lower(), "profile": r["target"],
            "target": r["scope"].lower(), "client": r["client"], "cache": "unknown", "metric": "gbps",
            "started": day.isoformat(), "value": value, "unit": "Gbps", "higher_is_better": True,
            "source": r["source"], "host": "", "git": "", "session": "", "file": f"{file.name}:{line}"}


def load(directory: Path) -> list[dict]:
    rows = []
    for file in sorted(directory.glob("*.csv")):
        with file.open(newline="") as f:
            for i, r in enumerate(csv.DictReader(f), start=2):
                if any((v or "").strip() for v in r.values()):
                    rows.append(_row(file, i, r))
    return rows
