"""Scenarios are config only: storage/scenarios/<name>/scenario.yaml."""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

from ibench_storage.profiles import expand

SCENARIOS = Path(__file__).resolve().parents[2] / "scenarios"


def load(name: str) -> dict:
    path = SCENARIOS / name / "scenario.yaml"
    if not path.exists():
        raise SystemExit(f"unknown scenario {name!r}; available: {', '.join(p.name for p in SCENARIOS.iterdir())}")
    return _walk(yaml.safe_load(path.read_text()))


def _walk(node):
    """Expand ${VAR} in every string so scenarios can name objects and prefixes from the environment."""
    if isinstance(node, dict):
        return {k: _walk(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_walk(v) for v in node]
    if isinstance(node, str):
        for var, default in re.findall(r"\$\{(\w+)(?::-([^}]*))?\}", node):
            if not default and var not in os.environ:
                raise SystemExit(f"scenario needs {var} (see the scenario README)")
    return expand(node)
