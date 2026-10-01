# network

TCP throughput and path probes. Results: `network/results/`.

```bash
# on the target: iperf3 -s -p 5201
uv run ibench-net iperf <host> --streams 1,8,16 --seconds 30 --client <label> --tag system=<name>
uv run ibench-net iperf <host> -R          # server sends: the direction data flows to a reader
uv run ibench-net path <host>              # RTT, loss, PMTU, hop count
```

Add `--scope wan` (across the internet or a cloud) or `--scope internal` (within the site) so the report groups results that way.

`--streams` sweeps parallel streams and writes one result per value; the first `--omit 2` seconds are excluded. Each
run records the sender's congestion control and retransmits. `path` uses ping and falls back to TCP connect time
(`--port`, default 443) when ICMP is blocked; `method` in the record says which.

## Results from runs made elsewhere

```bash
uv run ibench-net import run.json --scope internal --client <host> --profile <target> --source "<ticket or channel>"
uv run ibench-net import pair1.txt pair2.txt pair3.txt pair4.txt --scope internal --client <hosts> --profile <target> \
    --reverse --date 2026-10-05          # four host pairs run together: results are summed
```

Accepts `iperf3 -J` JSON or the plain-text report. Text has no date or direction, so pass `--date` and `--reverse`
(server sent) or `--to-server`. Numbers without an output file (earlier results, other tools) go in
[`reports/intake/network.csv`](../reports/intake/network.csv); see [reports/README.md](../reports/README.md).

## Servers

An iperf3 server needs a login on the target. Without one, run tests between hosts you do control, or ask the target's
administrators to leave `iperf3 -s -p <port>` running (iperf3 serves one test at a time, so use one port per host pair,
for example 5201-5208) and open those ports to the client hosts only.

## Method

- Run `path` first to confirm reachability, then iperf3 to a specific node and through the load balancer separately.
- Use 8 or more streams: a single TCP flow is often limited over long paths.
- Both ends need a modern congestion control (BBR) and large socket buffers; the record shows the client's.
- Keep one record per direction (`to-server`, `from-server`); they differ.

## Gotchas

- Stale iperf3 processes cap results; kill them before a run.
- Paths crossing a cloud provider's network often do not pass jumbo frames; `path` reports the PMTU.
