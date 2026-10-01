"""Argument and output helpers shared by the suite CLIs."""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from ibench.env import ROOT, client_label
from ibench.results import Run, now, parse_tags, save

SITES = ROOT / "sites"


def add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--client", default=client_label(), help="vantage point label (default: Slurm partition or hostname)")
    p.add_argument("--site", help="site description sites/<name>.yaml recorded with the result (default: the client label)")
    p.add_argument("--cache", choices=("cold", "warm", "unknown"), default="unknown")
    p.add_argument("--tag", action="append", default=[], metavar="K=V", help="metadata, e.g. gateway=new")
    p.add_argument("--results-dir", type=Path, help="default: <suite>/results")


def add_repeat(p: argparse.ArgumentParser) -> None:
    p.add_argument("--repeat", type=int, default=1, help="run N times; the report shows median and spread")


def site(name: str) -> dict | None:
    path = SITES / f"{name}.yaml"
    return yaml.safe_load(path.read_text()) if path.exists() else None


def finish(run: Run, args: argparse.Namespace, suite: str, session: str = "") -> None:
    run.cache = args.cache
    run.tags = {**run.tags, "client": args.client, **({"session": session} if session else {}), **parse_tags(args.tag)}
    if desc := site(args.site or args.client):
        run.env = {**run.env, "site": desc}
    path = save(run, args.results_dir or ROOT / suite / "results")
    p = run.primary
    print(f"{run.name}: {p['name']}={p['value']:.4g} {p['unit']} -> {path}")


def repeat(args: argparse.Namespace, suite: str, produce) -> None:
    """Call produce() (a list of Runs) --repeat times; repeats share a session so the report aggregates them."""
    session = now()
    for _ in range(getattr(args, "repeat", 1)):
        for run in produce():
            finish(run, args, suite, session)
