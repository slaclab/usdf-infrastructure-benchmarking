import json

from ibench import Run, metric, save
from ibench.results import parse_tags


def test_save_roundtrip(tmp_path):
    run = Run("network", "iperf3", metric("gbps", 12.5, "Gbps"), profile="host a", started="2026-09-30T10:00:00+00:00")
    path = save(run, tmp_path)
    assert path.name == "20260930T100000Z_iperf3_host-a.json"
    data = json.loads(path.read_text())
    assert data["primary"]["value"] == 12.5 and data["cache"] == "unknown"


def test_parse_tags():
    assert parse_tags(["gateway=new", "note=a=b"]) == {"gateway": "new", "note": "a=b"}


def test_capture_records_node_shape():
    from ibench.env import capture

    env = capture()
    assert {"cpus", "cpus_online", "cpu_quota", "threads_per_core", "load_1m", "nics", "os", "mem_gib"} <= set(env)
    assert isinstance(env["nics"], list)
