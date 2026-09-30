from ibench_net import iperf, path

PING = """--- host ping statistics ---
20 packets transmitted, 20 received, 0% packet loss, time 19031ms
rtt min/avg/max/mdev = 0.106/0.210/0.334/0.050 ms
"""
TRACE = """ 1?: [LOCALHOST]                      pmtu 9000
 1:  172.24.48.10                                          0.334ms
 2:  172.24.7.7                                            0.106ms reached
     Resume: pmtu 9000 hops 2 back 2
"""


def test_parse_iperf():
    out = {"end": {"sum_sent": {"bits_per_second": 31e9, "retransmits": 7},
                   "sum_received": {"bits_per_second": 30e9},
                   "cpu_utilization_percent": {"host_total": 12.0, "remote_total": 5.0},
                   "sender_tcp_congestion": "bbr"}}
    m = iperf.parse(out)
    assert m["gbps"] == 30.0 and m["retransmits"] == 7 and m["congestion"] == "bbr"


def test_parse_ping_and_tracepath():
    assert path.parse_ping(PING) == {"rtt_min_ms": 0.106, "rtt_avg_ms": 0.21, "rtt_max_ms": 0.334,
                                     "rtt_mdev_ms": 0.05, "loss_pct": 0.0}
    assert path.parse_tracepath(TRACE) == {"pmtu": 9000, "hops": 2}


def test_tcp_rtt_fallback():
    import socket
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen()
    m = path.tcp_rtt("127.0.0.1", srv.getsockname()[1], 3)
    srv.close()
    assert m["loss_pct"] == 0 and m["rtt_avg_ms"] > 0
