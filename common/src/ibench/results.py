"""One JSON record per benchmark invocation, shared by every suite."""
from __future__ import annotations

import getpass
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


def _prefixes() -> list[tuple[str, str]]:
    """Absolute paths that identify the user or the checkout, longest first, with their neutral replacements."""
    root = Path(__file__).resolve().parents[3]
    pairs = {(str(p), tag) for p, tag in ((root, "<repo>"), (root.resolve(), "<repo>"), (Path.home(), "~"), (Path.home().resolve(), "~"))}
    return sorted(pairs, key=lambda x: -len(x[0]))


def scrub(obj, prefixes: list[tuple[str, str]] | None = None, user: str | None = None):
    """Replace home and checkout paths, and the login name as a path component, in every string of a record."""
    prefixes = _prefixes() if prefixes is None else prefixes
    if user is None:
        try:
            user = getpass.getuser()
        except (KeyError, OSError):
            user = ""
        user = "" if user == "root" else user
    pat = re.compile(rf"(?<=/){re.escape(user)}(?=/|$)") if user else None
    if isinstance(obj, str):
        for p, tag in prefixes:
            obj = obj.replace(p, tag)
        return pat.sub("user", obj) if pat else obj
    if isinstance(obj, dict):
        return {k: scrub(v, prefixes, user) for k, v in obj.items()}
    if isinstance(obj, list):
        return [scrub(v, prefixes, user) for v in obj]
    return obj


def save(run: Run, results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.fromisoformat(run.started).strftime("%Y%m%dT%H%M%SZ")
    label = re.sub(r"[^\w.-]+", "-", "_".join(filter(None, (run.name, run.scenario, run.profile))))
    path = results_dir / f"{stamp}_{label}.json"
    path.write_text(json.dumps(scrub(json.loads(json.dumps(asdict(run), default=str))), indent=2) + "\n")
    return path
