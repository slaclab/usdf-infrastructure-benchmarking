"""Argument and output helpers shared by the suite CLIs."""
from __future__ import annotations

import argparse
from pathlib import Path

from ibench.env import ROOT, client_label
from ibench.results import Run, parse_tags, save


def add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--client", default=client_label(), help="vantage point label (default: Slurm partition or hostname)")
    p.add_argument("--cache", choices=("cold", "warm", "unknown"), default="unknown")
    p.add_argument("--tag", action="append", default=[], metavar="K=V", help="metadata, e.g. gateway=new")
    p.add_argument("--results-dir", type=Path, help="default: <suite>/results")


def finish(run: Run, args: argparse.Namespace, suite: str) -> None:
    run.cache = args.cache
    run.tags = {**run.tags, "client": args.client, **parse_tags(args.tag)}
    path = save(run, args.results_dir or ROOT / suite / "results")
    p = run.primary
    print(f"{run.name}: {p['name']}={p['value']:.4g} {p['unit']} -> {path}")
