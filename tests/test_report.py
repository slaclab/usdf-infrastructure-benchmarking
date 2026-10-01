import json

from ibench_report import consolidate


def _write(root, name, value, started, hib=True, session=""):
    d = root / "storage/results"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps({
        "suite": "storage", "name": "micro.throughput", "scenario": "s", "profile": "p", "cache": "warm",
        "tags": {"client": "hopper", **({"session": session} if session else {})}, "started": started,
        "primary": {"name": "peak_gbps", "value": value, "unit": "Gbps", "higher_is_better": hib}}))


def test_regression_and_improvement(tmp_path):
    _write(tmp_path, "a.json", 10.0, "2026-01-01T00:00:00+00:00")
    _write(tmp_path, "b.json", 7.0, "2026-02-01T00:00:00+00:00")
    rows = consolidate.load(tmp_path)
    (key, pts), = consolidate.group(rows).items()
    assert consolidate.compare(pts, 0.1)[0] == "REGRESSED"
    assert "## Regressions" in consolidate.render(rows)
    _write(tmp_path, "c.json", 9.9, "2026-03-01T00:00:00+00:00")
    pts = list(consolidate.group(consolidate.load(tmp_path)).values())[0]
    assert consolidate.compare(pts, 0.1)[0] == "improved"


def test_repo_legacy_loads():
    rows = consolidate.load()
    assert any(r["source"].startswith("Jira DM-54361") for r in rows)
    sdfiana = [r for r in rows if r["client"] == "sdfiana"]
    assert [r["value"] for r in sdfiana] == [2.6, 37]


def test_repeats_in_a_session_collapse_to_median_and_range(tmp_path):
    for i, v in enumerate((9.0, 10.0, 12.0)):
        _write(tmp_path, f"r{i}.json", v, f"2026-01-01T00:00:0{i}+00:00", session="s1")
    _write(tmp_path, "z.json", 8.0, "2026-02-01T00:00:00+00:00", session="s2")
    (key, pts), = consolidate.group(consolidate.load(tmp_path)).items()
    assert [(p["value"], p["n"], p["min"], p["max"]) for p in pts] == [(10.0, 3, 9.0, 12.0), (8.0, 1, 8.0, 8.0)]
    assert consolidate.compare(pts, 0.1)[0] == "REGRESSED"
    _write(tmp_path, "y.json", 9.5, "2026-03-01T00:00:00+00:00", session="s3")
    _write(tmp_path, "y2.json", 9.7, "2026-03-01T00:00:01+00:00", session="s3")
    assert "n=2, 9.5-9.7" in consolidate.render(consolidate.load(tmp_path))
