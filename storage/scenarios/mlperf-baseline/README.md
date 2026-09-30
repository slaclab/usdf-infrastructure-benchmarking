# mlperf-baseline

Stock MLPerf Storage UNet3D (about 140 MB samples, one per file), 1 to 32 simulated H100 accelerators. Gives a number
comparable with published MLPerf results and the client-side ceiling of one node.

```bash
uv run ibench-storage mlperf datagen mlperf-baseline --profile posix     # 5x client RAM
uv run ibench-storage mlperf run mlperf-baseline --profile posix --cache cold
```

Smoke test first: `--mem-factor 0.1 --run unet3d-acc2`.
