"""Load endpoint profiles from storage/profiles.yaml."""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

PROFILES = Path(__file__).resolve().parents[2] / "profiles.yaml"


def expand(value):
    if not isinstance(value, str):
        return value
    return re.sub(r"\$\{(\w+)(?::-([^}]*))?\}",
                  lambda m: os.environ.get(m[1], m[2] if m[2] is not None else ""), value)


def load(name: str, **override) -> dict:
    profiles = yaml.safe_load(PROFILES.read_text())
    if name not in profiles:
        raise SystemExit(f"unknown profile {name!r}; available: {', '.join(profiles)}")
    prof = {"name": name, **{k: expand(v) for k, v in profiles[name].items()}}
    prof.update({k: v for k, v in override.items() if v})
    missing = [k for k in ("root", "endpoint", "bucket") if k in prof and not prof[k]]
    if missing:
        raise SystemExit(f"profile {name!r}: set {', '.join(missing)} (see storage/profiles.yaml)")
    return prof


def target(prof: dict) -> str:
    """Where the data lives; part of a result's series."""
    return prof.get("root") or f"{prof['endpoint']}/{prof['bucket']}"
