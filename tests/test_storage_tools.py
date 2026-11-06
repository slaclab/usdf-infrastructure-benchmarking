import json
import shutil
from pathlib import Path

import pytest

from ibench_storage import engine, fio, mix, warp

FIX = Path(__file__).parent / "fixtures"
PROF = {"name": "s3", "kind": "s3", "endpoint": "https://a.example,https://b.example", "bucket": "b",
        "region": "us-east-1", "lookup": "path"}


def test_warp_parse_multi_sized():
    m = warp.parse(FIX / "warp_get_multi_sized.json.zst")
    assert m["errors"] == 0 and m["requests"] > 0
    assert m["gbps"] == pytest.approx(m["mbps"] * 8 / 1000)
    assert 0 < m["p50_ms"] <= m["p99_ms"] and "req_p99_ms" not in m


def test_warp_parse_single_sized_has_request_p99():
    m = warp.parse(FIX / "warp_get_single_sized.json.zst")
    assert m["req_p99_ms"] >= m["req_avg_ms"] > 0 and m["latency_basis"] == "ttfb"


def _fixture(name):
    import zstandard

    return json.loads(zstandard.ZstdDecompressor().stream_reader((FIX / name).open("rb")).read())


def test_warp_latency_skips_size_classes_without_first_byte():
    op = _fixture("warp_get_multi_sized.json.zst")["by_op_type"]["GET"]
    full = warp._latency(op)
    buckets = [b for segs in op["requests_by_client"].values() for seg in segs for b in seg["multi_sized_requests"]["by_size"]]
    buckets[0].pop("first_byte")
    partial = warp._latency(op)
    assert 0 < partial["p50_ms"] <= partial["p99_ms"] and partial["req_avg_ms"] == pytest.approx(full["req_avg_ms"])
    for b in buckets:
        b.pop("first_byte", None)
    assert "p50_ms" not in warp._latency(op) and warp._latency(op)["req_avg_ms"] > 0


def test_warp_latency_tolerates_null_size_classes():
    op = {"requests_by_client": {"c": [{"multi_sized_requests": {"by_size": None}}, {"single_sized_requests": None}, None]}}
    assert warp._latency(op) == {"latency_basis": "ttfb"}
    assert warp._latency({"requests_by_client": None}) == {"latency_basis": "ttfb"}


def test_latency_step_without_first_byte_fails_clearly(tmp_path):
    from ibench_storage import steps

    p = steps.Planned("read.x", 1, "p/", engine.Job("warp", ["warp"], {}, tmp_path, None))
    with pytest.raises(SystemExit, match="reported no latency"):
        steps.record({"name": "s3", "kind": "s3"}, p, {"gbps": 1.0}, {"label": "x", "metric": "latency"}, "s", 1.0)


def test_warp_parse_rejects_empty(tmp_path):
    import zstandard

    p = tmp_path / "x.json.zst"
    p.write_bytes(zstandard.ZstdCompressor().compress(json.dumps({"by_op_type": {}}).encode()))
    with pytest.raises(SystemExit, match="too few samples"):
        warp.parse(p)


def test_warp_command_is_read_only_and_keeps_secrets_off_the_command_line(tmp_path, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAEXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "s3cr3t-value")
    j = warp.job(PROF, "ibench/data/visit_image/", 8, 30, 64 * 1024, tmp_path / "r")
    cmd = j.cmd
    assert {"--list-existing", "--noclear", "--tls"} <= set(cmd) and cmd[1] == "get"
    assert cmd[cmd.index("--host") + 1] == "a.example,b.example"
    assert cmd[cmd.index("--range-size") + 1] == "65536" and "--range" in cmd
    assert "AKIAEXAMPLE" not in " ".join(cmd) and "s3cr3t-value" not in " ".join(cmd)
    assert j.env["WARP_ACCESS_KEY"] == "AKIAEXAMPLE" and j.env["WARP_SECRET_KEY"] == "s3cr3t-value"


def test_warp_needs_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    with pytest.raises(SystemExit, match="AWS_ACCESS_KEY_ID"):
        warp.job(PROF, "p/", 1, 10, 0, tmp_path / "r")


def test_warp_rejects_mixed_schemes():
    with pytest.raises(SystemExit, match="mix http and https"):
        warp.hosts("http://a,https://b")


def test_fio_parse_fixture():
    m = fio.parse(FIX / "fio_read.json")
    assert m["gbps"] > 0 and 0 < m["p50_ms"] <= m["p99_ms"] and m["errors"] == 0


def test_fio_job_uses_job_file_and_never_creates_files(tmp_path):
    files = [f"/data/tile_{i:05d}.png" for i in range(2000)]
    j = fio.job(files, 4, 10, 16384, False, True, tmp_path / "r")
    text = (tmp_path / "r.fio").read_text()
    assert text.count("filename=") == 2000 and "allow_file_create=0" in text and "rw=randread" in text
    assert "direct=1" in text and all(len(a) < 4096 for a in j.cmd)


@pytest.mark.skipif(not shutil.which("fio"), reason="fio not installed")
def test_fio_end_to_end_leaves_files_untouched(tmp_path):
    files = []
    for i in range(3):
        f = tmp_path / f"f{i}.bin"
        f.write_bytes(bytes(1 << 20))
        files.append(str(f))
    m = engine.execute(fio.job(files, 2, 2, 65536, True, False, tmp_path / "raw" / "r"))
    assert m["gbps"] > 0 and sorted(p.stat().st_size for p in tmp_path.glob("f*.bin")) == [1 << 20] * 3


def test_mix_reports_ratio_against_solo(monkeypatch):
    calls = []

    def fake_plan(prof, step, scenario, base):
        return [type("P", (), {"name": f"read.{step['label']}", "level": 1, "prefix": "p/",
                               "job": type("J", (), {"tool": "t", "cmd": ["t"], "label": step["label"]})()})()]

    def fake_execute(job):
        calls.append(job.label)
        together = job.label.endswith("together")
        return {"gbps": 5.0 if together else 10.0, "p99_ms": 40.0 if together else 10.0}

    def fake_record(prof, p, metrics, step, scenario, seconds):
        from ibench import Run, metric
        primary = (metric("p99_ms", metrics["p99_ms"], "ms", False) if step.get("metric") == "latency"
                   else metric("gbps", metrics["gbps"], "Gbps"))
        return Run("storage", p.name, primary, metrics, {}, scenario, "s3", tags={"target": "t"})

    monkeypatch.setattr(mix.steps, "plan", fake_plan)
    monkeypatch.setattr(mix.steps, "record", fake_record)
    monkeypatch.setattr(mix.engine, "execute", fake_execute)
    loads = {"a": {"data": "x", "concurrency": 1, "duration_s": 5},
             "b": {"data": "y", "concurrency": 1, "duration_s": 5, "metric": "latency"}}
    runs = {r.name: r for r in mix.run({"name": "s3"}, loads, "interference/x", "base")}
    assert runs["mix.a.ratio"].primary["value"] == pytest.approx(0.5)
    assert runs["mix.b.ratio"].primary["value"] == pytest.approx(4.0)
    assert runs["mix.b.ratio"].primary["higher_is_better"] is False
    assert sorted(calls) == ["a.solo", "a.together", "b.solo", "b.together"]


def test_mix_requires_duration_and_single_concurrency():
    with pytest.raises(SystemExit, match="duration_s"):
        mix.run({"name": "s3"}, {"a": {"data": "x", "concurrency": [1, 2]}}, "s", "b")
