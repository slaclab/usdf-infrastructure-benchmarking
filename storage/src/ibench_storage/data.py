"""Mock payloads: size classes from datasets.yaml written as random bytes (or JSON-lines text) under a base prefix."""
from __future__ import annotations

import functools
import io
import json
import os
import random
import re
import string
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

DATASETS = Path(__file__).resolve().parents[2] / "datasets.yaml"
UNITS = {"KiB": 1 << 10, "MiB": 1 << 20, "GiB": 1 << 30}
BLOCK = 8 << 20


def classes() -> dict:
    return yaml.safe_load(DATASETS.read_text())


def parse_size(s) -> int:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(KiB|MiB|GiB)", str(s))
    if not m:
        raise SystemExit(f"bad size {s!r}; use e.g. 512KiB, 100MiB, 1GiB")
    return int(float(m[1]) * UNITS[m[2]])


@functools.cache
def _noise() -> bytes:
    return os.urandom(BLOCK)


@functools.cache
def _text() -> bytes:
    rng = random.Random(0)
    vocab = ["".join(rng.choices(string.ascii_lowercase, k=rng.randint(2, 9))) for _ in range(5000)]
    lines = (json.dumps({"text": " ".join(rng.choices(vocab, k=150))}) + "\n" for _ in range(4000))
    return "".join(lines).encode()


class Payload(io.RawIOBase):
    """`size` bytes cycling through a shared block, started at a per-object offset so objects differ."""

    def __init__(self, size: int, seed: int, text: bool = False):
        self.block = _text() if text else _noise()
        self.left, self.pos = size, seed % len(self.block)

    def readable(self) -> bool:
        return True

    def read(self, n: int | None = -1) -> bytes:
        n = self.left if n is None or n < 0 else min(n, self.left)
        out = bytearray()
        while len(out) < n:
            take = min(n - len(out), len(self.block) - self.pos)
            out += self.block[self.pos:self.pos + take]
            self.pos = (self.pos + take) % len(self.block)
        self.left -= n
        return bytes(out)


def plan(name: str, spec: dict, scale: float) -> list[tuple[str, int]]:
    rng = random.Random(name)
    size, jitter = parse_size(spec["size"]), spec.get("jitter", 0.1)
    return [(f"{name}/{i:06d}.{spec.get('ext', 'bin')}", int(size * (1 + jitter * rng.uniform(-1, 1))))
            for i in range(max(1, round(spec["count"] * scale)))]


def generate(store, base: str, names: list[str], scale: float, workers: int, max_gb: float, dry_run: bool) -> int:
    """Write the classes under base/<class>/; objects that already exist are skipped, so reruns resume."""
    specs = classes()
    if unknown := [n for n in names if n not in specs]:
        raise SystemExit(f"unknown classes {unknown}; available: {', '.join(specs)}")
    files = [(f"{base}/{rel}", size, specs[n].get("kind") == "text")
             for n in names for rel, size in plan(n, specs[n], scale)]
    total = sum(s for _, s, _ in files)
    print(f"{len(files)} objects, {total / 1e9:.1f} GB under {base}/")
    if total > max_gb * 1e9:
        raise SystemExit(f"{total / 1e9:.0f} GB exceeds --max-gb {max_gb}; lower --scale or raise the limit")
    if dry_run:
        return total
    have = {k for k, _ in store.list(base + "/")}
    todo = [f for f in files if f[0] not in have]
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(lambda f: store.write(f[0], Payload(f[1], zlib.crc32(f[0].encode()), f[2])), todo))
    print(f"wrote {len(todo)}, skipped {len(files) - len(todo)} existing")
    return total
