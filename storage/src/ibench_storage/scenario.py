"""Scenarios are config only: storage/scenarios/<group>/<name>/scenario.yaml."""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

from ibench_storage.profiles import expand

SCENARIOS = Path(__file__).resolve().parents[2] / "scenarios"
DATA_PREFIX = "IBENCH_DATA_PREFIX"


def names() -> list[str]:
    return sorted(str(p.parent.relative_to(SCENARIOS)) for p in SCENARIOS.rglob("scenario.yaml"))


def load(name: str) -> dict:
    path = SCENARIOS / name / "scenario.yaml"
    if not path.exists():
        raise SystemExit(f"unknown scenario {name!r}; available: {', '.join(names())}")
    return _walk(yaml.safe_load(path.read_text()))


def base_prefix() -> str:
    """Where mock data lives: a key prefix on S3 or a directory under the POSIX root."""
    return os.environ.get(DATA_PREFIX, "ibench/data").strip("/")


def data_classes(scn: dict) -> list[str]:
    """Mock data classes a scenario reads, in order of first use."""
    steps = [*scn.get("steps", []), *scn.get("mix", {}).values(), *([scn["tokenize"]] if "tokenize" in scn else [])]
    return list(dict.fromkeys(s["data"] for s in steps if "data" in s))


def _walk(node):
    """Expand ${VAR} in every string; a variable without a default must be set."""
    if isinstance(node, dict):
        return {k: _walk(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_walk(v) for v in node]
    if isinstance(node, str):
        for var, default in re.findall(r"\$\{(\w+)(?::-([^}]*))?\}", node):
            if not default and var not in os.environ:
                raise SystemExit(f"scenario needs {var} (see the scenario README)")
    return expand(node)
