import io
import json

import pytest

from ibench_storage import data, profiles, scenario, tokens
from ibench_storage.store import Store


def posix(tmp_path):
    return {"name": "posix", "kind": "posix", "root": str(tmp_path)}


def test_parse_size():
    assert data.parse_size("100MiB") == 100 << 20 and data.parse_size("0.5GiB") == 1 << 29
    with pytest.raises(SystemExit):
        data.parse_size("12MB")


def test_payload_is_exact_size_and_objects_differ():
    a, b = data.Payload(3 << 20, 1).read(), data.Payload(3 << 20, 2).read()
    assert len(a) == len(b) == 3 << 20 and a != b


def test_plan_is_deterministic_and_scales():
    spec = data.classes()["visit_image"]
    full, small = data.plan("visit_image", spec, 1), data.plan("visit_image", spec, 0.05)
    assert len(full) == spec["count"] and len(small) == round(spec["count"] * 0.05)
    assert full[:3] == data.plan("visit_image", spec, 1)[:3]
    sizes = [s for _, s in full]
    assert 0.85 * (100 << 20) < min(sizes) and max(sizes) < 1.15 * (100 << 20)


def test_generate_guard_dry_run_and_resume(tmp_path, capsys):
    store = Store(posix(tmp_path))
    with pytest.raises(SystemExit, match="exceeds --max-gb"):
        data.generate(store, "b", ["raw_zip"], 1, 2, 1, False)
    data.generate(store, "b", ["forced_source"], 0.02, 2, 5, True)
    assert not list(tmp_path.rglob("*.parquet"))
    data.generate(store, "b", ["forced_source"], 0.02, 2, 5, False)
    n = len(list(tmp_path.rglob("*.parquet")))
    assert n == 4
    data.generate(store, "b", ["forced_source"], 0.02, 2, 5, False)
    assert f"skipped {n} existing" in capsys.readouterr().out


def test_generate_unknown_class(tmp_path):
    with pytest.raises(SystemExit, match="unknown classes"):
        data.generate(Store(posix(tmp_path)), "b", ["nope"], 1, 1, 1, False)


def test_store_posix_roundtrip(tmp_path):
    s = Store(posix(tmp_path))
    s.write("a/b/c.bin", io.BytesIO(b"hello"))
    assert s.list("a/") == [("a/b/c.bin", 5)] and s.read("a/b/c.bin") == b"hello"
    s.delete(["a/b/c.bin"])
    assert s.list("a/") == []


def test_every_scenario_loads_and_its_data_classes_exist(monkeypatch):
    monkeypatch.setenv("IBENCH_DATA_PREFIX", "x")
    known = data.classes()
    names = scenario.names()
    assert {"rubin-access/object-reads", "genesis/tokenization", "interference/dac-vs-genesis"} <= set(names)
    for n in names:
        assert set(scenario.data_classes(scenario.load(n))) <= set(known), n


def test_profile_env_expansion(monkeypatch):
    monkeypatch.setenv("IBENCH_POSIX_ROOT", "/x")
    assert profiles.load("posix")["root"] == "/x"
    monkeypatch.delenv("IBENCH_POSIX_ROOT")
    with pytest.raises(SystemExit, match="set root"):
        profiles.load("posix")


def test_tokenization_on_posix_shards(tmp_path, monkeypatch):
    prof = posix(tmp_path)
    store = Store(prof)
    for i in range(2):
        lines = "".join(json.dumps({"text": f"alpha beta gamma delta {i} " * 20}) + "\n" for _ in range(300))
        store.write(f"b/text_shard/{i:06d}.jsonl", io.BytesIO(lines.encode()))
    monkeypatch.setattr(tokens, "RAW", tmp_path / "raw" / "reads")
    run = tokens.run(prof, {"data": "text_shard", "label": "text"}, "genesis/tokenization", "b", workers=2)
    m = run.metrics
    assert m["docs"] == 600 and m["tokens"] > 600 and 0 <= m["io_share"] <= 1
    assert run.primary["name"] == "tokens_per_s" and run.primary["value"] > 0
    assert not list((tmp_path / "b").glob("tokenized/*/*.bin"))
