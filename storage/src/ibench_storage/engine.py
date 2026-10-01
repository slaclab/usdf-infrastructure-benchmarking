"""An external benchmark tool invocation: what to run and how to read its output."""
from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ibench.env import ROOT

RAW = Path(os.environ.get("IBENCH_RAW_DIR", ROOT / "storage/results/raw")) / "reads"


@dataclass
class Job:
    tool: str
    cmd: list[str]
    env: dict
    out: Path
    parse: Callable[[Path], dict]


def version(tool: str) -> str:
    try:
        r = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (r.stdout or r.stderr).strip().splitlines()[0] if r.returncode == 0 and (r.stdout or r.stderr) else ""


def execute(job: Job) -> dict:
    if not shutil.which(job.cmd[0]):
        raise SystemExit(f"{job.cmd[0]} not found; run storage/scripts/setup_tools.sh (see storage/README.md)")
    job.out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(job.cmd, env=job.env, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{job.tool} exited {r.returncode}: {(r.stderr or r.stdout).strip()[-600:]}")
    return job.parse(job.out)
