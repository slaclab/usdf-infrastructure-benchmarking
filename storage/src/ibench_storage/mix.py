"""Interference: run loads alone, then together in separate processes, and report the change in each."""
from __future__ import annotations

import multiprocessing as mp
import time

from ibench import Run, metric
from ibench_storage import profiles
from ibench_storage.steps import micro_run

START_DELAY_S = 3  # lets every process build its client before the shared start


def _child(prof: dict, step: dict, scenario: str, start_at: float, out) -> None:
    step = dict(step)
    test = step.pop("test")
    be = profiles.backend(prof)
    time.sleep(max(0.0, start_at - time.time()))
    out.put((step["label"], micro_run(test, be, prof, step, scenario)))


def _phase(prof: dict, loads: dict, scenario: str, names: list[str], phase: str,
           start: float | None = None) -> dict[str, Run]:
    ctx = mp.get_context("spawn")
    out = ctx.Queue()
    start = start or time.time() + START_DELAY_S
    procs = [ctx.Process(target=_child, args=(prof, {**loads[n], "label": f"{n}.{phase}"}, scenario, start, out))
             for n in names]
    for p in procs:
        p.start()
    runs = dict(out.get() for _ in procs)
    for p in procs:
        p.join()
    return {n: runs[f"{n}.{phase}"] for n in names}


def run(prof: dict, loads: dict, scenario: str, only: str | None = None, start_at: float | None = None) -> list[Run]:
    """Every load needs a duration_s so the loads overlap for the whole measurement.

    With `only`, run a single load (phase "together" when start_at is given): start the other loads on other
    hosts at the same start_at to measure interference across hosts; no ratio is computed then.
    """
    if missing := [n for n, s in loads.items() if not s.get("duration_s")]:
        raise SystemExit(f"loads without duration_s: {', '.join(missing)}")
    if only:
        if only not in loads:
            raise SystemExit(f"no load {only!r}; available: {', '.join(loads)}")
        return list(_phase(prof, loads, scenario, [only], "together" if start_at else "solo", start_at).values())
    solo = {n: _phase(prof, loads, scenario, [n], "solo")[n] for n in loads}
    both = _phase(prof, loads, scenario, list(loads), "together")
    out = [*solo.values(), *both.values()]
    for n in loads:
        s, t = solo[n].primary, both[n].primary
        ratio = t["value"] / s["value"] if s["value"] else float("nan")
        out.append(Run("storage", f"mix.{n}.ratio",
                       metric(f"{s['name']}_together_over_solo", ratio, "x", s["higher_is_better"]),
                       {"solo": s["value"], "together": t["value"], "unit": s["unit"]},
                       {"loads": list(loads)}, scenario, prof["name"], env=solo[n].env))
    return out
