"""Presigned-URL reads against a local moto S3 server, and the summary maths."""
import io
import os

import pytest

pytest.importorskip("moto")
from moto.server import ThreadedMotoServer

from ibench_storage import engine, signedurl, steps
from ibench_storage.store import Store


@pytest.fixture(scope="module")
def s3():
    server = ThreadedMotoServer(port=0)
    server.start()
    host, port = server.get_host_and_port()
    os.environ.update(AWS_ACCESS_KEY_ID="x", AWS_SECRET_ACCESS_KEY="y")
    prof = {"name": "s3", "kind": "s3", "endpoint": f"http://{host}:{port}", "bucket": "tmpsigned",
            "region": "us-east-1", "lookup": "path"}
    store = Store(prof)
    store.clients[0].create_bucket(Bucket="tmpsigned")
    for i in range(4):
        store.write(f"t/visit/{i}.fits", io.BytesIO(os.urandom(256 << 10)))
    yield prof
    server.stop()


@pytest.fixture(autouse=True)
def no_proxy(monkeypatch, tmp_path):
    for var in ("http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.delenv(var, raising=False)
        monkeypatch.delenv(var.upper(), raising=False)
    monkeypatch.setattr(engine, "RAW", tmp_path / "raw")


def test_signed_reads_whole_objects_with_timeline_and_no_secret(s3):
    before = Store(s3).list("t/visit/")
    step = {"label": "url", "prefix": "t/visit/", "signed": True, "concurrency": [2, 4], "duration_s": 3}
    runs = steps.run(s3, step, "rubin-access/test", "")
    assert [r.name for r in runs] == ["read.url.c2", "read.url.c4"]
    for r in runs:
        m = r.metrics
        assert m["errors"] == 0 and r.primary["value"] > 0 and m["objects_per_s"] > 0 and m["p99_ms"] > 0
        assert len(m["timeline_gbps"]) == len(m["timeline_errors"]) == 3
        assert m["min_1s_gbps"] <= m["median_1s_gbps"]
        assert r.env["tool"]["name"] == "signed-url" and "ibench_storage.signedurl" in r.env["tool"]["cmd"]
        assert "y" not in r.env["tool"]["cmd"] and not any("X-Amz-Signature" in c for c in r.env["tool"]["cmd"])
    assert Store(s3).list("t/visit/") == before


def test_signed_ranged_reads_and_keepalive(s3):
    step = {"label": "rng", "prefix": "t/visit/", "signed": True, "keepalive": True, "range_kib": 16,
            "concurrency": 2, "duration_s": 2, "metric": "latency"}
    (run,) = steps.run(s3, step, "rubin-access/test", "")
    assert run.primary["name"] == "p99_ms" and run.metrics["errors"] == 0 and run.metrics["objects_per_s"] > 0


def test_signed_step_needs_s3():
    with pytest.raises(SystemExit, match="needs an S3 profile"):
        steps.plan({"name": "posix", "kind": "posix", "root": "/tmp"}, {"label": "x", "prefix": "p", "signed": True},
                   "s", "")


def test_summary_percentiles_timeline_and_failure():
    part = {"ttfb": [0.01, 0.02, 0.03, 0.04], "dur": [0.1, 0.2, 0.3, 0.4], "objects": 4, "errors": 1,
            "first_error": "OSError: HTTP 503", "bytes": [125_000_000, 0, 250_000_000], "err": [0, 1, 0]}
    m = signedurl.summarise([part], 3, 2)
    assert m["gbps"] == pytest.approx(375_000_000 * 8 / 3 / 1e9)
    assert m["timeline_gbps"] == [1.0, 0.0, 2.0] and m["timeline_errors"] == [0, 1, 0]
    assert (m["min_1s_gbps"], m["median_1s_gbps"]) == (0.0, 1.0)
    assert m["p50_ms"] == pytest.approx(20) and m["p99_ms"] == pytest.approx(40) and m["requests"] == 5


def test_parse_rejects_all_errors(tmp_path):
    path = tmp_path / "r.json"
    path.write_text('{"requests": 3, "errors": 3, "first_error": "ConnectionRefusedError"}')
    with pytest.raises(SystemExit, match="ConnectionRefusedError"):
        signedurl.parse(path)
