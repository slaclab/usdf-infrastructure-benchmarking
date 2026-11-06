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
    assert {"cpus", "cpus_online", "cpu_quota", "threads_per_core", "load_1m", "nics", "gpus", "os", "mem_gib"} <= set(env)
    assert isinstance(env["nics"], list) and isinstance(env["gpus"], list)


def test_gpus_parsed_from_nvidia_smi(monkeypatch):
    from ibench import env

    monkeypatch.setattr(env, "sh", lambda *a, **k: "NVIDIA A100-SXM4-80GB, 81920, 550.54\nNVIDIA A100-SXM4-80GB, 81920, 550.54")
    assert env._gpus() == [{"name": "NVIDIA A100-SXM4-80GB", "memory_mib": 81920, "driver": "550.54"}] * 2
    monkeypatch.setattr(env, "sh", lambda *a, **k: None)
    assert env._gpus() == []


def test_scrub_replaces_home_checkout_and_login_name():
    from ibench.results import scrub

    prefixes = [("/home/jo/repo", "<repo>"), ("/home/jo", "~")]
    rec = {"cmd": ["/home/jo/repo/.venv/bin/tool", "--out", "/home/jo/repo/results/raw/a"], "n": 3,
           "alias": "/other/jo/x", "keep": "/data/joint/y"}
    assert scrub(rec, prefixes, "jo") == {"cmd": ["<repo>/.venv/bin/tool", "--out", "<repo>/results/raw/a"], "n": 3,
                                          "alias": "/other/user/x", "keep": "/data/joint/y"}
