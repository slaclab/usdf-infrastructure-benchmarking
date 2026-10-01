"""warp and the Store against a local moto S3 server; skipped when warp is missing."""
import os
import shutil

import pytest

pytest.importorskip("moto")
from moto.server import ThreadedMotoServer

from ibench_storage import data, engine, steps, warp
from ibench_storage.store import Store

pytestmark = pytest.mark.skipif(not shutil.which(warp.BIN), reason="warp not installed")


@pytest.fixture(scope="module")
def s3():
    server = ThreadedMotoServer(port=0)
    server.start()
    host, port = server.get_host_and_port()
    os.environ.update(AWS_ACCESS_KEY_ID="x", AWS_SECRET_ACCESS_KEY="y")
    prof = {"name": "s3", "kind": "s3", "endpoint": f"http://{host}:{port}", "bucket": "tmpbench",
            "region": "us-east-1", "lookup": "path"}
    Store(prof).clients[0].create_bucket(Bucket="tmpbench")
    yield prof
    server.stop()


def test_get_reads_existing_objects_and_deletes_nothing(s3, tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "RAW", tmp_path / "raw")
    store = Store(s3)
    data.generate(store, "t", ["small_image"], 0.02, 2, 1, False)
    before = store.list("t/")
    assert len(before) == 40
    step = {"label": "imgs", "data": "small_image", "concurrency": [1, 4], "duration_s": 6}
    runs = steps.run(s3, step, "rubin-access/test", "t")
    assert [r.name for r in runs] == ["read.imgs.c1", "read.imgs.c4"]
    assert all(r.metrics["errors"] == 0 and r.primary["value"] > 0 for r in runs)
    assert store.list("t/") == before
    assert runs[0].env["tool"]["cmd"][:2] == [warp.BIN, "get"] and "--noclear" in runs[0].env["tool"]["cmd"]


def test_missing_prefix_fails_before_running(s3):
    with pytest.raises(SystemExit, match="nothing under"):
        steps.plan(s3, {"label": "x", "data": "absent", "concurrency": 1}, "s", "t")
