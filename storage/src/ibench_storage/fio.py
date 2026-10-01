"""fio read runs over files that already exist: command and result parsing. Never creates or writes files."""
from __future__ import annotations

import json
import os
from pathlib import Path

from ibench_storage.engine import Job

BIN = os.environ.get("FIO_BIN", "fio")


def job(files: list[str], concurrency: int, duration_s: float, block_bytes: int, sequential: bool, direct: bool,
        base: Path) -> Job:
    """The file list goes in a job file: --filename values are limited to 4096 characters."""
    options = ["name=ibench", f"rw={'read' if sequential else 'randread'}", f"bs={block_bytes}",
               f"numjobs={concurrency}", "group_reporting", "ioengine=psync", f"direct={int(direct)}", "time_based",
               f"runtime={int(duration_s)}", "ramp_time=2", "allow_file_create=0", "invalidate=1",
               "file_service_type=random", *(f"filename={f}" for f in files)]
    spec = Path(f"{base}.fio")
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("[ibench]\n" + "\n".join(options[1:]) + "\n")
    cmd = [BIN, str(spec), "--output-format=json", f"--output={base}.json"]
    return Job("fio", cmd, dict(os.environ), Path(f"{base}.json"), parse)


def parse(path: Path) -> dict:
    j = json.loads(path.read_text())["jobs"][0]
    r, pct = j["read"], j["read"]["clat_ns"]["percentile"]
    if j.get("error") or not r["io_bytes"]:
        raise SystemExit(f"fio read failed (error {j.get('error')}, {r['io_bytes']} bytes read)")
    return {"gbps": r["bw_bytes"] * 8 / 1e9, "mbps": r["bw_bytes"] / 1e6, "iops": r["iops"], "bytes": r["io_bytes"],
            "measure_s": r["runtime"] / 1000, "p50_ms": pct["50.000000"] / 1e6, "p99_ms": pct["99.000000"] / 1e6,
            "latency_basis": "io", "errors": j.get("error", 0), "raw": str(path)}
