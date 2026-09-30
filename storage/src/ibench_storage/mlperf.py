"""Wrapper over stock mlpstorage. Its checkout and venv are built by scripts/setup_mlperf.sh."""
from __future__ import annotations

import json
import math
import os
import shlex
import statistics
import subprocess
import sys
import time
from pathlib import Path

from ibench import Run, capture, metric
from ibench.env import ROOT, mem_gib

BIN = Path(os.environ.get("MLPSTORAGE_BIN", ROOT / ".vendor/mlcommons-storage/.venv/bin/mlpstorage"))
# engine output; must be on a different filesystem than the dataset (MLPerf rule 3.4.2)
RAW = Path(os.environ.get("IBENCH_RAW_DIR", ROOT / "storage/results/raw"))
LOGS = ROOT / "storage/results/logs"
ORG = "slac"
PRIMARY = ("train_io_mean_MB_per_second", "MiB/s")  # DLIO names it MB but divides by 1024**2
EXTRA = shlex.split(os.environ.get("MLPSTORAGE_EXTRA", ""))  # e.g. --allow-run-as-root, --skip-fs-separation-gate


def dlio_params(m: dict, dataset: str, mem_factor: float) -> dict:
    """Dataset params with num_files_train sized to mem_factor x client RAM (MLPerf rule 3.1.2 uses 5x)."""
    params = dict(m["datasets"][dataset].get("params", {}))
    file_bytes = int(params.get("dataset.num_samples_per_file", 1)) * m["record_bytes"]
    files = math.ceil(mem_factor * mem_gib() * 1024**3 / file_bytes)
    return {**params, "dataset.num_files_train": files}


def _storage(prof: dict) -> str:
    return "file" if prof["kind"] == "posix" else "object"


def _data_dir(prof: dict, scenario: str, dataset: str) -> str:
    rel = f"ibench/{scenario}/{dataset}"
    return str(Path(prof["root"]) / rel) if prof["kind"] == "posix" else rel


def _env(prof: dict) -> dict:
    env = {**os.environ, "PATH": f"{BIN.parent}{os.pathsep}{os.environ['PATH']}"}  # mlpstorage finds dlio_benchmark on PATH
    if prof["kind"] == "s3":
        if "," in prof["endpoint"] or prof.get("anonymous") in ("1", "true"):
            raise SystemExit("MLPerf object mode needs one signed endpoint; lists and anonymous access are micro-only")
        env.update(AWS_ENDPOINT_URL=prof["endpoint"], BUCKET=prof["bucket"], MLPS_S3_BUCKET=prof["bucket"],
                   AWS_REGION=prof.get("region", "us-east-1"), STORAGE_LIBRARY=prof.get("library", "s3dlio"))
    return env


def _cmd(m: dict, phase: str, prof: dict, scenario: str, dataset: str, params: dict, extra: list[str]) -> list[str]:
    cmd = [str(BIN), m["mode"], "training", m["model"], phase, _storage(prof),
           "--systemname", prof["name"], "--results-dir", str(RAW),
           "--data-dir", _data_dir(prof, scenario, dataset), *EXTRA, *extra]
    return cmd + ["--params", *(f"{k}={v}" for k, v in params.items())] if params else cmd


def _accel_args(m: dict, accelerators: int) -> list[str]:
    return ["--accelerator-type", m["accelerator_type"], "--num-accelerators", str(accelerators),
            "--client-host-memory-in-gb", str(int(mem_gib())), "--oversubscribe"]


def _init() -> None:
    if not (RAW / "mlperf-results.yaml").exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(BIN), "init", ORG, str(RAW)], check=True)


def _exec(cmd: list[str], env: dict, log: Path) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    # cwd=RAW: DLIO writes relative paths such as checkpoints/ into the working directory
    with subprocess.Popen(cmd, env=env, cwd=RAW, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as p, \
            log.open("w") as f:
        for line in p.stdout:
            sys.stdout.write(line)
            f.write(line)
    if p.returncode:
        raise SystemExit(f"mlpstorage exited {p.returncode}; log: {log}")


def _summary(model: str, since: float) -> dict:
    found = [p for p in RAW.rglob("summary.json")
             if f"/training/{model}/run/" in str(p) and p.stat().st_mtime >= since]
    if not found:
        raise SystemExit("mlpstorage produced no run summary.json")
    return json.loads(max(found, key=lambda p: p.stat().st_mtime).read_text())["metric"]


def _flatten(metrics: dict) -> dict:
    return {k: statistics.fmean(v) if isinstance(v, list) and v else v for k, v in metrics.items()}


def _selected(m: dict, only: str | None) -> list[dict]:
    runs = [r for r in m["runs"] if only in (None, r["name"])]
    if not runs:
        raise SystemExit(f"no run named {only!r}")
    return runs


def datagen(scn: str, m: dict, prof: dict, only: str | None, mem_factor: float, procs: int) -> None:
    _init()
    for ds in dict.fromkeys(r["dataset"] for r in _selected(m, only)):
        params = dlio_params(m, ds, mem_factor)
        cmd = _cmd(m, "datagen", prof, scn, ds, params, ["--num-processes", str(procs)])
        _exec(cmd, _env(prof), LOGS / f"{int(time.time())}_{scn}_datagen_{ds}.log")


def configview(scn: str, m: dict, prof: dict, only: str | None, mem_factor: float) -> None:
    _init()
    for r in _selected(m, only):
        params = {**dlio_params(m, r["dataset"], mem_factor), **m.get("params", {}), **r.get("params", {})}
        subprocess.run(_cmd(m, "configview", prof, scn, r["dataset"], params, _accel_args(m, r["accelerators"])),
                       env=_env(prof), cwd=RAW, check=True)


def run(scn: str, m: dict, prof: dict, only: str | None, mem_factor: float) -> list[Run]:
    _init()
    out = []
    for r in _selected(m, only):
        params = {**dlio_params(m, r["dataset"], mem_factor), **m.get("params", {}), **r.get("params", {})}
        cmd = _cmd(m, "run", prof, scn, r["dataset"], params, _accel_args(m, r["accelerators"]))
        start = time.time()
        _exec(cmd, _env(prof), LOGS / f"{int(start)}_{scn}_{r['name']}.log")
        metrics = _flatten(_summary(m["model"], start))
        if PRIMARY[0] not in metrics:
            raise SystemExit(f"{PRIMARY[0]} missing from summary; keys: {sorted(metrics)}")
        info = {"mode": m["mode"], "model": m["model"], "accelerator_type": m["accelerator_type"],
                "accelerators": r["accelerators"], "dataset": r["dataset"], "mem_factor": mem_factor,
                "dlio": params}
        out.append(Run("storage", f"mlperf.{r['name']}", metric(PRIMARY[0], metrics[PRIMARY[0]], PRIMARY[1]),
                       metrics, info, scn, prof["name"], env=capture(prof.get("root")),
                       duration_s=time.time() - start,
                       tags={"target": prof.get("root") or f"{prof['endpoint']}/{prof['bucket']}"}))
    return out
