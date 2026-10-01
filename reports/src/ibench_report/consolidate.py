"""Consolidate result JSON from network/, storage/ and reports/legacy/ into history.csv and latest.md."""
from __future__ import annotations

import csv
import json
import re
import statistics
from pathlib import Path

from ibench.env import ROOT

SOURCES = ("network/results", "storage/results", "reports/legacy")
SERIES = ("suite", "name", "scenario", "profile", "target", "client", "cache", "metric")
COLUMNS = (*SERIES, "started", "value", "unit", "higher_is_better", "source", "host", "git", "session", "file")


def load(root: Path = ROOT) -> list[dict]:
    rows = []
    for src in SOURCES:
        for p in sorted((root / src).glob("*.json")):
            r = json.loads(p.read_text())
            pr, env = r["primary"], r.get("env") or {}
            rows.append({
                "suite": r["suite"], "name": r["name"], "scenario": r.get("scenario", ""),
                "profile": r.get("profile", ""), "target": (r.get("tags") or {}).get("target", ""),
                "client": (r.get("tags") or {}).get("client", ""),
                "cache": r.get("cache", "unknown"), "metric": pr["name"], "started": r["started"],
                "value": pr["value"], "unit": pr["unit"], "higher_is_better": pr.get("higher_is_better", True),
                "source": r.get("source", "ibench"), "host": env.get("host", ""),
                "git": (env.get("git") or {}).get("sha") or "", "session": (r.get("tags") or {}).get("session", ""),
                "file": str(p.relative_to(root)),
            })
    return sorted(rows, key=lambda r: (r["started"], r["file"]))


def _collapse(rows: list[dict]) -> list[dict]:
    """Repeats from one session become one point: the median, with the count and the min and max."""
    sessions: dict[str, list[dict]] = {}
    for r in rows:
        sessions.setdefault(r["session"] or r["file"], []).append(r)
    points = []
    for grp in sessions.values():
        vals = sorted(g["value"] for g in grp)
        points.append({**grp[-1], "value": statistics.median(vals), "n": len(vals), "min": vals[0], "max": vals[-1]})
    return sorted(points, key=lambda r: r["started"])


def group(rows: list[dict]) -> dict[tuple, list[dict]]:
    series: dict[tuple, list[dict]] = {}
    for r in rows:
        series.setdefault(tuple(r[k] for k in SERIES), []).append(r)
    return {key: _collapse(pts) for key, pts in series.items()}


def compare(pts: list[dict], threshold: float) -> tuple[str, float | None]:
    if len(pts) < 2:
        return "new", None
    last, prev = pts[-1], pts[-2]
    delta = (last["value"] - prev["value"]) / abs(prev["value"]) if prev["value"] else 0.0
    if abs(delta) < threshold:
        return "flat", delta
    return ("improved" if (delta > 0) == last["higher_is_better"] else "REGRESSED"), delta


def _fmt(v: float) -> str:
    return f"{v:.4g}"


def render(rows: list[dict], threshold: float = 0.10) -> str:
    groups = group(rows)
    lines = ["# Latest performance", "",
             f"{len(rows)} runs in {len(groups)} series, {rows[0]['started'][:10]} to {rows[-1]['started'][:10]}. "
             f"Status compares the latest session with the previous one in the same series (regression or "
             f"improvement beyond {threshold:.0%}); repeats in one session show as their median with n and range. "
             f"Per-run detail is in `history.csv`.", ""]
    table = []
    for key, pts in sorted(groups.items()):
        status, delta = compare(pts, threshold)
        best = (max if pts[-1]["higher_is_better"] else min)(p["value"] for p in pts)
        last = pts[-1]
        spread = f" (n={last['n']}, {_fmt(last['min'])}-{_fmt(last['max'])})" if last["n"] > 1 else ""
        series = " / ".join(filter(None, (*key[:6], key[6] if key[6] != "unknown" else "")))
        table.append((key, status, [
            series, f"{_fmt(last['value'])} {last['unit']}{spread}", last["started"][:10],
            _fmt(pts[-2]["value"]) if len(pts) > 1 else "-", f"{delta:+.1%}" if delta is not None else "-",
            _fmt(best), status, str(len(pts))]))
    header = "| Series (suite / test / scenario / profile / target / client / cache) | Latest | Date | Previous | Change | Best | Status | Runs |\n|---|---|---|---|---|---|---|---|"
    bad = [t for t in table if t[1] == "REGRESSED"]
    if bad:
        lines += ["## Regressions", "", header, *("| " + " | ".join(t[2]) + " |" for t in bad), ""]
    for suite in sorted({k[0] for k, _, _ in table}):
        lines += [f"## {suite}", "", header,
                  *("| " + " | ".join(t[2]) + " |" for t in table if t[0][0] == suite), ""]
    return "\n".join(lines)


def write(root: Path = ROOT, threshold: float = 0.10) -> list[dict]:
    rows = load(root)
    if not rows:
        raise SystemExit("no results found")
    out = root / "reports"
    with (out / "history.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, COLUMNS)
        w.writeheader()
        w.writerows(rows)
    (out / "latest.md").write_text(render(rows, threshold) + "\n")
    return rows


def plots(rows: list[dict], root: Path = ROOT) -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = root / "reports/plots"
    out.mkdir(exist_ok=True)
    n = 0
    for key, pts in group(rows).items():
        if len(pts) < 2:
            continue
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot([p["started"][:10] for p in pts], [p["value"] for p in pts], "o-")
        ax.set_title(" / ".join(filter(None, key[:6])), fontsize=8)
        ax.set_ylabel(f"{key[7]} ({pts[0]['unit']})")
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(out / (re.sub(r"[^\w.-]+", "-", "_".join(filter(None, key))) + ".png"), dpi=120)
        plt.close(fig)
        n += 1
    return n
