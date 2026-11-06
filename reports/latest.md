# Latest performance

125 runs in 56 series, 2026-03-10 to 2026-11-06. Status compares the latest session with the previous one in the same series (regression or improvement beyond 10%); repeats in one session show as their median with n and range. Per-run detail is in `history.csv`.

## network

| Series (suite / test / scenario / profile / target / client / cache) | Latest | Date | Previous | Change | Best | Status | Runs |
|---|---|---|---|---|---|---|---|
| network / iperf3 / 4-pairs / sdfemb101-203 / sdfiana028-031 | 320 Gbps | 2026-09-15 | - | - | 320 | new | 1 |
| network / iperf3 / from-server / s3df-dtn / gcp-tier1 | 30 Gbps | 2026-03-10 | - | - | 30 | new | 1 |
| network / iperf3 / to-server / s3df-dtn / gcp-tier1 | 20 Gbps | 2026-03-10 | - | - | 20 | new | 1 |
| network / iperf3 / to-server / s3df-dtn / gcp-us-central1 | 12 Gbps | 2026-03-10 | - | - | 12 | new | 1 |
| network / iperf3 / to-server / sdfdatas3 / gcp-tier1-x2 | 60.6 Gbps | 2026-03-17 | - | - | 60.6 | new | 1 |
| network / path / sdfdatas3.slac.stanford.edu / nersc-perlmutter-gpu | 1.334 ms | 2026-11-06 | 1.325 | +0.7% | 1.325 | flat | 2 |

## storage

| Series (suite / test / scenario / profile / target / client / cache) | Latest | Date | Previous | Change | Best | Status | Runs |
|---|---|---|---|---|---|---|---|
| storage / hats.ceiling.t1 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter | 2.163 Gbps | 2026-11-05 | - | - | 2.163 | new | 1 |
| storage / hats.ceiling.t1 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 2.946 Gbps (n=3, 2.653-3.151) | 2026-11-06 | - | - | 2.946 | new | 1 |
| storage / hats.ceiling.t16 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter | 5.625 Gbps | 2026-11-05 | - | - | 5.625 | new | 1 |
| storage / hats.ceiling.t16 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 5.429 Gbps (n=3, 5.012-5.493) | 2026-11-06 | - | - | 5.429 | new | 1 |
| storage / hats.ceiling.t32 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter | 5.39 Gbps | 2026-11-05 | - | - | 5.39 | new | 1 |
| storage / hats.ceiling.t32 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 4.991 Gbps (n=3, 4.968-5.27) | 2026-11-06 | - | - | 4.991 | new | 1 |
| storage / hats.ceiling.t4 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter | 4.99 Gbps | 2026-11-05 | - | - | 4.99 | new | 1 |
| storage / hats.ceiling.t4 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 6.33 Gbps (n=3, 4.915-6.336) | 2026-11-06 | - | - | 6.33 | new | 1 |
| storage / hats.ceiling.t8 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter | 5.564 Gbps | 2026-11-05 | - | - | 5.564 | new | 1 |
| storage / hats.ceiling.t8 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 5.587 Gbps (n=3, 5.111-6.073) | 2026-11-06 | - | - | 5.587 | new | 1 |
| storage / hats.lsdb.n16 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter | 2.687 Gbps | 2026-11-05 | - | - | 2.687 | new | 1 |
| storage / hats.lsdb.n64.t1 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 1.467 Gbps (n=3, 1.422-1.479) | 2026-11-06 | - | - | 1.467 | new | 1 |
| storage / hats.lsdb.n64.t16 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 2.672 Gbps (n=3, 2.567-2.673) | 2026-11-06 | - | - | 2.672 | new | 1 |
| storage / hats.lsdb.n64.t32 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 2.748 Gbps (n=3, 2.72-2.755) | 2026-11-06 | - | - | 2.748 | new | 1 |
| storage / hats.lsdb.n64.t4 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 2.751 Gbps (n=3, 2.74-2.843) | 2026-11-06 | - | - | 2.751 | new | 1 |
| storage / hats.lsdb.n64.t8 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 2.728 Gbps (n=3, 2.713-2.838) | 2026-11-06 | - | - | 2.728 | new | 1 |
| storage / hats.npd_direct.n16 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter | 3.068 Gbps | 2026-11-05 | - | - | 3.068 | new | 1 |
| storage / hats.npd_direct.n64.t1 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 1.641 Gbps (n=3, 1.625-1.653) | 2026-11-06 | - | - | 1.641 | new | 1 |
| storage / hats.npd_direct.n64.t16 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 2.829 Gbps (n=3, 2.771-2.94) | 2026-11-06 | - | - | 2.829 | new | 1 |
| storage / hats.npd_direct.n64.t32 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 2.891 Gbps (n=3, 2.801-2.908) | 2026-11-06 | - | - | 2.891 | new | 1 |
| storage / hats.npd_direct.n64.t4 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 3.046 Gbps (n=3, 2.983-3.048) | 2026-11-06 | - | - | 3.046 | new | 1 |
| storage / hats.npd_direct.n64.t8 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 2.95 Gbps (n=3, 2.913-3.02) | 2026-11-06 | - | - | 2.95 | new | 1 |
| storage / hats.pa_arrow.n16 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter | 0.1114 Gbps | 2026-11-05 | - | - | 0.1114 | new | 1 |
| storage / hats.pa_arrow_native.n16 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter | 4.495 Gbps | 2026-11-05 | - | - | 4.495 | new | 1 |
| storage / hats.pa_arrow_native.n64.t1 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 2.62 Gbps (n=3, 2.498-2.635) | 2026-11-06 | - | - | 2.62 | new | 1 |
| storage / hats.pa_arrow_native.n64.t16 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 6.94 Gbps (n=3, 5.782-7.66) | 2026-11-06 | - | - | 6.94 | new | 1 |
| storage / hats.pa_arrow_native.n64.t32 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 6.664 Gbps (n=3, 6.054-7.674) | 2026-11-06 | - | - | 6.664 | new | 1 |
| storage / hats.pa_arrow_native.n64.t4 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 7.472 Gbps (n=3, 7.068-7.891) | 2026-11-06 | - | - | 7.472 | new | 1 |
| storage / hats.pa_arrow_native.n64.t8 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 7.155 Gbps (n=3, 7.029-7.9) | 2026-11-06 | - | - | 7.155 | new | 1 |
| storage / hats.pa_arrow_ranges.n64.t1 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 1.734 Gbps (n=3, 1.703-1.758) | 2026-11-06 | - | - | 1.734 | new | 1 |
| storage / hats.pa_arrow_ranges.n64.t16 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 2.985 Gbps (n=3, 2.983-3.012) | 2026-11-06 | - | - | 2.985 | new | 1 |
| storage / hats.pa_arrow_ranges.n64.t32 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 2.947 Gbps (n=3, 2.923-3.058) | 2026-11-06 | - | - | 2.947 | new | 1 |
| storage / hats.pa_arrow_ranges.n64.t4 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 3.051 Gbps (n=3, 3.032-3.054) | 2026-11-06 | - | - | 3.051 | new | 1 |
| storage / hats.pa_arrow_ranges.n64.t8 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 3.004 Gbps (n=3, 2.955-3.025) | 2026-11-06 | - | - | 3.004 | new | 1 |
| storage / hats.pa_pandas_arrow.n16 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter | 0.1194 Gbps | 2026-11-05 | - | - | 0.1194 | new | 1 |
| storage / hats.pa_pandas_numpy.n16 / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter | 0.1142 Gbps | 2026-11-05 | - | - | 0.1142 | new | 1 |
| storage / hats.stat / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter | 6.047 ms | 2026-11-05 | - | - | 6.047 | new | 1 |
| storage / hats.stat / genesis/hats-reads / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks/lsdb/gaia_dr3/gaia / nersc-perlmutter-gpu | 5.953 ms (n=3, 5.625-6.255) | 2026-11-06 | - | - | 5.953 | new | 1 |
| storage / micro.throughput / s3-remote-read / s3 / gcp-dev-rsp-tier1 | 3.55 Gbps | 2026-03-16 | - | - | 3.55 | new | 1 |
| storage / micro.throughput / s3-remote-read / s3 / gcp-prod-rsp | 2.98 Gbps | 2026-03-16 | - | - | 2.98 | new | 1 |
| storage / micro.throughput / s3-remote-read / s3 / gcp-us-west1-vm | 5.64 Gbps | 2026-03-16 | - | - | 5.64 | new | 1 |
| storage / micro.throughput / s3-remote-read / s3 / sdfiana | 37 Gbps | 2026-06-24 | 2.6 | +1323.1% | 37 | improved | 2 |
| storage / micro.throughput / s3-remote-read / s3 / usdf-rsp | 5.2 Gbps | 2026-03-16 | - | - | 5.2 | new | 1 |
| storage / read.gaia-objects.c1 / adhoc / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks / nersc-perlmutter-gpu | 3.335 Gbps (n=3, 3.303-3.378) | 2026-11-06 | - | - | 3.335 | new | 1 |
| storage / read.gaia-objects.c128 / adhoc / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks / nersc-perlmutter-gpu | 42.93 Gbps (n=3, 42.41-43.33) | 2026-11-06 | - | - | 42.93 | new | 1 |
| storage / read.gaia-objects.c256 / adhoc / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks / nersc-perlmutter-gpu | 26.22 Gbps (n=3, 23.94-38.92) | 2026-11-06 | - | - | 26.22 | new | 1 |
| storage / read.gaia-objects.c32 / adhoc / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks / nersc-perlmutter-gpu | 40 Gbps (n=3, 35.81-46.6) | 2026-11-06 | - | - | 40 | new | 1 |
| storage / read.gaia-objects.c64 / adhoc / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks / nersc-perlmutter-gpu | 46.86 Gbps (n=3, 32.87-51.2) | 2026-11-06 | 50.03 | -6.3% | 50.03 | flat | 2 |
| storage / read.gaia-objects.c8 / adhoc / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks / nersc-perlmutter-gpu | 9.894 Gbps (n=3, 3.431-12.61) | 2026-11-06 | - | - | 9.894 | new | 1 |
| storage / read.smoke / adhoc / s3 / https://sdfdatas3.slac.stanford.edu/rubin-benchmarks / nersc-perlmutter-gpu | 10.07 Gbps | 2026-11-06 | - | - | 10.07 | new | 1 |

