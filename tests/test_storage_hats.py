"""HATS read path over POSIX and over a local moto S3 server; needs the hats extra."""
import os

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("lsdb")
pytest.importorskip("moto")
import lsdb
from moto.server import ThreadedMotoServer

from ibench_storage import hats
from ibench_storage.store import Store

SPEC = {"catalog": "cat/gaia", "column": "phot_g_mean_mag", "partitions": 0, "threads": 2, "ceiling": [2]}


@pytest.fixture(scope="module")
def catalog(tmp_path_factory):
    root = tmp_path_factory.mktemp("hats")
    rng = np.random.default_rng(1)
    n = 6000
    df = pd.DataFrame({"ra": rng.uniform(0, 360, n), "dec": np.degrees(np.arcsin(rng.uniform(-1, 1, n))),
                       "phot_g_mean_mag": rng.normal(18, 2, n), "other": rng.normal(size=n)})
    lsdb.from_dataframe(df, catalog_name="gaia", ra_column="ra", dec_column="dec", lowest_order=1, highest_order=2,
                        partition_rows=500).write_catalog(root / "cat", overwrite=True)
    return root


@pytest.fixture(scope="module")
def s3(catalog):
    server = ThreadedMotoServer(port=0)
    server.start()
    host, port = server.get_host_and_port()
    os.environ.update(AWS_ACCESS_KEY_ID="x", AWS_SECRET_ACCESS_KEY="y")
    prof = {"name": "s3", "kind": "s3", "endpoint": f"http://{host}:{port}", "bucket": "tmpbench",
            "region": "us-east-1", "lookup": "path"}
    client = Store(prof).clients[0]
    client.create_bucket(Bucket="tmpbench")
    for p in (catalog / "cat").rglob("*"):
        if p.is_file():
            client.upload_file(str(p), "tmpbench", f"cat/{p.relative_to(catalog / 'cat')}")
    yield prof
    server.stop()


def _check(runs, n_variants):
    by = {r.name: r for r in runs}
    reads = [r for r in runs if r.name.startswith("hats.") and ".n" in r.name]
    assert len(reads) == n_variants
    assert len({round(r.metrics["mean"], 6) for r in reads}) == 1
    assert all(r.primary["value"] > 0 and r.params["partitions"] > 1 for r in reads)
    assert by["hats.stat"].primary["unit"] == "ms" and by["hats.ceiling.t2"].primary["value"] > 0
    assert all(r.tags["target"].endswith("/cat/gaia") for r in runs)
    return reads


def test_posix_reads(catalog):
    prof = {"name": "posix", "kind": "posix", "root": str(catalog)}
    reads = _check(hats.run(prof, SPEC, "genesis/hats-reads"), 5)
    assert all("wire_mb" not in r.metrics for r in reads)


def test_s3_reads_count_wire_bytes(s3):
    reads = _check(hats.run(s3, SPEC, "genesis/hats-reads"), 7)
    counted = [r for r in reads if not r.name.startswith("hats.pa_arrow_native")]
    assert all(r.metrics["wire_mb"] > 0 and r.metrics["over_read"] >= 1 for r in counted)
    assert all(r.params["endpoint"] == s3["endpoint"] for r in reads)


def test_variants_selection(catalog):
    prof = {"name": "posix", "kind": "posix", "root": str(catalog)}
    runs = hats.run(prof, {**SPEC, "variants": ["lsdb", "pa_arrow_native"], "ceiling": []}, "genesis/hats-reads")
    assert [r.params["variant"] for r in runs if "variant" in r.params] == ["lsdb"]
    with pytest.raises(SystemExit, match="unknown variant"):
        hats.run(prof, {**SPEC, "variants": ["nope"]}, "genesis/hats-reads")


def test_s3_rejects_several_endpoints(s3):
    with pytest.raises(SystemExit, match="one endpoint"):
        hats.Source({**s3, "endpoint": s3["endpoint"] + ",http://other"}, SPEC)
