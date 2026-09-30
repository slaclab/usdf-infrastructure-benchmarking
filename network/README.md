# network

TCP throughput and path probes. Results: `network/results/`.

```bash
# on the target: iperf3 -s -p 5201
uv run ibench-net iperf <host> --streams 1,8,16 --seconds 30 --client <label> --tag system=<name>
uv run ibench-net iperf <host> -R          # server sends: the direction data flows to a reader
uv run ibench-net path <host>              # RTT, loss, PMTU, hop count
```

`--streams` sweeps parallel streams and writes one result per value; the first `--omit 2` seconds are excluded. Each
run records the sender's congestion control and retransmits. `path` uses ping and falls back to TCP connect time
(`--port`, default 443) when ICMP is blocked; `method` in the record says which.

## Method

- Run `path` first to confirm reachability, then iperf3 to a specific node and through the load balancer separately.
- Use 8 or more streams: a single TCP flow is often limited over long paths.
- Both ends need a modern congestion control (BBR) and large socket buffers; the record shows the client's.
- Keep one record per direction (`to-server`, `from-server`); they differ.

## Gotchas

- Stale iperf3 processes cap results; kill them before a run.
- Paths crossing a cloud provider's network often do not pass jumbo frames; `path` reports the PMTU.
