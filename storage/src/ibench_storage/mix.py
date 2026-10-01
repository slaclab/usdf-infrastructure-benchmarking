"""Interference: run loads alone, then together, and report the change in each."""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

from ibench import Run, metric
from ibench_storage import engine, steps


def _phase(prof: dict, loads: dict, scenario: str, base: str, names: list[str], phase: str,
           start_at: float | None = None) -> dict[str, Run]:
    planned = {n: steps.plan(prof, {**loads[n], "label": f"{n}.{phase}"}, scenario, base)[0] for n in names}
    if start_at:
        time.sleep(max(0.0, start_at - time.time()))
    t0 = time.time()
    with ThreadPoolExecutor(len(planned)) as ex:
        results = dict(zip(planned, ex.map(lambda p: engine.execute(p.job), planned.values())))
    return {n: steps.record(prof, planned[n], results[n], {**loads[n], "label": f"{n}.{phase}"}, scenario,
                            time.time() - t0) for n in names}


def run(prof: dict, loads: dict, scenario: str, base: str, only: str | None = None,
        start_at: float | None = None) -> list[Run]:
    """Every load needs duration_s so the loads overlap for the whole measurement and use a single concurrency.

    With `only`, run one load (phase "together" when start_at is given): start the other loads on other hosts at
    the same start_at to measure interference across hosts; no ratio is computed then.
    """
    if bad := [n for n, s in loads.items() if not s.get("duration_s") or isinstance(s.get("concurrency"), list)]:
        raise SystemExit(f"loads need duration_s and a single concurrency: {', '.join(bad)}")
    if only:
        if only not in loads:
            raise SystemExit(f"no load {only!r}; available: {', '.join(loads)}")
        phase = "together" if start_at else "solo"
        return list(_phase(prof, loads, scenario, base, [only], phase, start_at).values())
    solo = {n: _phase(prof, loads, scenario, base, [n], "solo")[n] for n in loads}
    both = _phase(prof, loads, scenario, base, list(loads), "together")
    out = [*solo.values(), *both.values()]
    for n in loads:
        s, t = solo[n].primary, both[n].primary
        ratio = t["value"] / s["value"] if s["value"] else float("nan")
        out.append(Run("storage", f"mix.{n}.ratio",
                       metric(f"{s['name']}_together_over_solo", ratio, "x", s["higher_is_better"]),
                       {"solo": s["value"], "together": t["value"], "unit": s["unit"]},
                       {"loads": list(loads)}, scenario, prof["name"], env=solo[n].env,
                       tags={"target": solo[n].tags["target"]}))
    return out
