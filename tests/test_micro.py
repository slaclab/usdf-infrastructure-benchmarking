import pytest

from ibench_storage import micro, mix, profiles, scenario
from ibench_storage.backends import S3, Posix


@pytest.fixture
def be(tmp_path):
    (tmp_path / "d").mkdir()
    for i in range(4):
        (tmp_path / "d" / f"f{i}.bin").write_bytes(bytes(3_000_000))
    return Posix(str(tmp_path))


def test_pct():
    xs = list(range(1, 101))
    assert micro.pct(xs, 50) == 50 and micro.pct(xs, 99) == 99 and micro.pct(xs, 100) == 100


def test_throughput_reads_whole_object(be):
    m = micro.throughput(be, "d/f0.bin", [1, 4], iterations=2, chunk=1 << 20)
    assert m["size_bytes"] == 3_000_000 and set(m["levels"]) == {1, 4}
    assert m["peak_gbps"] > 0 and m["peak_concurrency"] in (1, 4)


def test_latency_and_bulk(be):
    files = be.list("d")
    assert len(files) == 4
    lat = micro.latency(be, files, n=50, size=65536, concurrency=2)
    assert lat["p50_ms"] <= lat["p99_ms"] <= lat["max_ms"]
    objs = micro.select(be, "d", max_objects=3, max_bytes=10**9)
    assert len(objs) == 3
    assert micro.bulk(be, objs, 2)["bytes"] == 9_000_000


def test_duration_loads_overlap_window(be):
    files = be.list("d")
    lat = micro.latency(be, files, n=0, size=65536, concurrency=2, duration_s=0.3)
    assert lat["n"] > 2
    b = micro.bulk(be, files, 2, duration_s=0.3)
    assert b["objects"] > len(files) and b["wall_s"] >= 0.3


def test_profile_expansion(monkeypatch):
    monkeypatch.setenv("IBENCH_S3_ENDPOINT", "https://e")
    monkeypatch.setenv("IBENCH_S3_BUCKET", "b")
    p = profiles.load("s3")
    assert p["endpoint"] == "https://e" and p["bucket"] == "b" and p["region"] == "us-east-1"
    monkeypatch.delenv("IBENCH_S3_BUCKET")
    with pytest.raises(SystemExit):
        profiles.load("s3")


def test_s3_endpoints_round_robin():
    s3 = S3("https://a.example,https://b.example", "b", "us-east-1", anonymous=True)
    hosts = [s3._client().meta.endpoint_url for _ in range(4)]
    assert hosts == ["https://a.example", "https://b.example"] * 2


def test_scenarios_load(monkeypatch):
    for var in ("IBENCH_S3_KEY", "IBENCH_S3_PREFIX"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(SystemExit):
        scenario.load("s3-remote-read")
    monkeypatch.setenv("IBENCH_S3_KEY", "k")
    monkeypatch.setenv("IBENCH_S3_PREFIX", "p/")
    assert scenario.load("s3-remote-read")["micro"][0]["key"] == "k"
    assert set(scenario.load("mixed-load")["mix"]) == {"sequential", "small"}
    assert scenario.load("parquet-training")["mlperf"]["params"]["train.computation_time"] == 0


def test_mix_reports_ratio(tmp_path, monkeypatch):
    (tmp_path / "d").mkdir()
    for i in range(3):
        (tmp_path / "d" / f"f{i}.bin").write_bytes(bytes(2_000_000))
    monkeypatch.setenv("IBENCH_POSIX_ROOT", str(tmp_path))
    monkeypatch.setattr(mix, "START_DELAY_S", 0.5)
    loads = {"seq": {"test": "bulk", "prefix": "d", "concurrency": 2, "duration_s": 0.5},
             "small": {"test": "latency", "prefix": "d", "size": 4096, "duration_s": 0.5}}
    runs = {r.name: r for r in mix.run(profiles.load("posix"), loads, "m")}
    assert set(runs) == {"micro.bulk.seq.solo", "micro.latency.small.solo", "micro.bulk.seq.together",
                         "micro.latency.small.together", "mix.seq.ratio", "mix.small.ratio"}
    assert runs["mix.small.ratio"].primary["higher_is_better"] is False
    assert runs["mix.seq.ratio"].metrics["together"] == runs["micro.bulk.seq.together"].primary["value"]
