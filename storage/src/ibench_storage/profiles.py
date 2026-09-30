"""Load endpoint profiles from storage/profiles.yaml."""
from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

from ibench_storage.backends import S3, Posix

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


def backend(prof: dict):
    if prof["kind"] == "posix":
        return Posix(prof["root"])
    return S3(prof["endpoint"], prof["bucket"], prof.get("region"), prof.get("anonymous") in ("1", "true", True))
