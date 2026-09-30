from __future__ import annotations

import argparse

from ibench_report import consolidate


def main() -> None:
    p = argparse.ArgumentParser(prog="ibench-report", description="Consolidate results into reports/.")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="write reports/history.csv and reports/latest.md")
    b.add_argument("--threshold", type=float, default=0.10, help="relative change flagged as regression/improvement")
    b.add_argument("--plots", action="store_true", help="also write reports/plots/*.png (needs the plots extra)")
    a = p.parse_args()
    rows = consolidate.write(threshold=a.threshold)
    print(f"{len(rows)} runs -> reports/history.csv, reports/latest.md")
    if a.plots:
        print(f"{consolidate.plots(rows)} plots -> reports/plots/")
