"""Host, network and filesystem context recorded with every result."""
from __future__ import annotations

import os
import platform
import re
import socket
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SLURM_KEYS = ("SLURM_JOB_ID", "SLURM_JOB_PARTITION", "SLURM_JOB_NODELIST", "SLURM_JOB_ACCOUNT", "SLURM_JOB_QOS",
              "SLURM_JOB_GPUS", "SLURM_CPUS_ON_NODE", "SLURM_MEM_PER_NODE")
TCP_KEYS = (
    "ipv4.tcp_congestion_control", "core.default_qdisc", "core.rmem_max",
    "core.wmem_max", "ipv4.tcp_rmem", "ipv4.tcp_wmem",
)


def sh(*cmd: str, timeout: int = 10) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _read(path: str) -> str | None:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def _cgroup_gib() -> float | None:
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        if (v := _read(path)) and v.isdigit():
            return int(v) / 1024**3
    return None


def cpus() -> int:
    return len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count() or 1


def mem_gib() -> float:
    """Memory visible to the benchmark: IBENCH_MEM_GIB, Slurm allocation, cgroup limit, else MemTotal."""
    if env := os.environ.get("IBENCH_MEM_GIB"):
        return float(env)
    if (mb := os.environ.get("SLURM_MEM_PER_NODE", "0")).isdigit() and int(mb) > 0:
        return int(mb) / 1024
    m = re.search(r"MemTotal:\s+(\d+) kB", _read("/proc/meminfo") or "")
    total = int(m[1]) / 1024**2 if m else 0.0
    cg = _cgroup_gib()
    return min(total, cg) if cg and total else total or cg or 0.0


def client_label() -> str:
    return os.environ.get("SLURM_JOB_PARTITION") or socket.gethostname().split(".")[0]


def mount_of(path: str) -> dict | None:
    real, best = os.path.realpath(path), None
    for line in (_read("/proc/mounts") or "").splitlines():
        src, mp, fstype, opts, *_ = line.split()
        if real == mp or real.startswith(mp.rstrip("/") + "/"):
            if best is None or len(mp) > len(best["mountpoint"]):
                best = {"mountpoint": mp, "source": src, "fstype": fstype, "options": opts}
    return best


def capture(path: str | None = None) -> dict:
    cpu = re.search(r"model name\s*:\s*(.+)", _read("/proc/cpuinfo") or "")
    root = str(ROOT)
    return {
        "host": socket.gethostname(),
        "kernel": platform.release(),
        "cpu": cpu[1] if cpu else platform.processor(),
        "cpus": cpus(),
        "mem_gib": round(mem_gib(), 1),
        "slurm": {k[6:].lower(): os.environ[k] for k in SLURM_KEYS if k in os.environ},
        "tcp": {k: _read("/proc/sys/net/" + k.replace(".", "/")) for k in TCP_KEYS},
        "mount": mount_of(path) if path else None,
        "git": {
            "sha": sh("git", "-C", root, "rev-parse", "--short", "HEAD"),
            "dirty": bool(sh("git", "-C", root, "status", "--porcelain")),
        },
        "iperf3": (sh("iperf3", "--version") or "").splitlines()[:1],
    }
