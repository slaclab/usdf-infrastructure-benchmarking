"""One JSON record per benchmark invocation, shared by every suite."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def metric(name: str, value: float, unit: str, higher_is_better: bool = True) -> dict:
    return {"name": name, "value": value, "unit": unit, "higher_is_better": higher_is_better}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Run:
    suite: str
    name: str
    primary: dict
    metrics: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    scenario: str = ""
    profile: str = ""
    cache: str = "unknown"
    tags: dict = field(default_factory=dict)
    env: dict = field(default_factory=dict)
    started: str = field(default_factory=now)
    duration_s: float = 0.0
    source: str = "ibench"


def parse_tags(items: list[str]) -> dict:
    return dict(i.split("=", 1) for i in items)


def save(run: Run, results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromisoformat(run.started).strftime("%Y%m%dT%H%M%SZ")
    label = re.sub(r"[^\w.-]+", "-", "_".join(filter(None, (run.name, run.scenario, run.profile))))
    path = results_dir / f"{stamp}_{label}.json"
    path.write_text(json.dumps(asdict(run), indent=2, default=str) + "\n")
    return path
