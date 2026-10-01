from pathlib import Path

import pytest

from ibench_net import importer
from ibench_report import consolidate, intake

FIX = Path(__file__).parent / "fixtures"
HEADER = "date,source,scope,client,target,direction,value,unit,tool,streams,pairs\n"


def write(tmp_path, *rows):
    d = tmp_path / "reports/intake"
    d.mkdir(parents=True)
    (d / "network.csv").write_text(HEADER + "".join(r + "\n" for r in rows))
    return d


def test_rows_convert_units_and_name_series(tmp_path):
    d = write(tmp_path,
              "2026-09-15,Slack channel,internal,sdfiana,sdfemb,to-server,320,Gbps,iperf3,5,4",
              "2026-09-30,Slack channel,internal,sdfiana,sdfemb,to-server,\"23,920\",MiB/s,,,",
              "2026-03-10,ticket,wan,gcp-tier1,s3df-dtn,from-server,30,,,10,")
    a, b, c = intake.load(d)
    assert (a["name"], a["target"], a["scenario"], a["value"]) == ("iperf3.p5.x4", "internal", "to-server", 320)
    assert b["name"] == "iperf3" and b["value"] == pytest.approx(23920 * 8 * 1.048576e-3)
    assert c["name"] == "iperf3.p10" and c["unit"] == "Gbps" and c["started"] == "2026-03-10"


@pytest.mark.parametrize("row,msg", [
    ("2026-13-01,s,wan,c,t,to-server,1", "date"),
    ("2026-09-01,s,lan,c,t,to-server,1", "scope"),
    ("2026-09-01,s,wan,c,t,up,1", "direction"),
    ("2026-09-01,s,wan,c,t,to-server,fast", "not a number"),
    ("2026-09-01,,wan,c,t,to-server,1", "missing source"),
    ("2026-09-01,s,wan,c,t,to-server,1,Tbps", "unit"),
])
def test_bad_rows_name_the_line(tmp_path, row, msg):
    with pytest.raises(SystemExit, match=rf"network.csv line 2: .*{msg}"):
        intake.load(write(tmp_path, row))


def test_intake_rows_join_the_history(tmp_path):
    write(tmp_path, "2026-03-10,ticket,wan,gcp,dtn,to-server,12,Gbps,iperf3,10,",
          "2026-09-10,ticket,wan,gcp,dtn,to-server,6,Gbps,iperf3,10,")
    (key, pts), = consolidate.group(consolidate.load(tmp_path)).items()
    assert key[:5] == ("network", "iperf3.p10", "to-server", "dtn", "wan")
    assert consolidate.compare(pts, 0.1)[0] == "REGRESSED"


def test_import_json_and_text():
    j = importer.parse_file(FIX / "iperf3_P4.json")
    assert j["streams"] == 4 and j["reverse"] is False and j["gbps"] > 1 and j["started"].startswith("2026")
    t = importer.parse_file(FIX / "iperf3_P4.txt")
    assert t["streams"] == 4 and t["reverse"] is None and t["gbps"] == pytest.approx(j["gbps"], rel=0.3)
    one = importer.parse_file(FIX / "iperf3_P1.txt")
    assert one["streams"] == 1 and one["gbps"] > 1


def test_import_rejects_unrelated_text(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("hello")
    with pytest.raises(ValueError, match="no iperf3"):
        importer.parse_file(f)
