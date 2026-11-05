"""HATS catalog read path: the same columns of the same partitions read with pyarrow, nested-pandas and lsdb, from a
POSIX root or an S3 bucket. Needs the `hats` extra."""
from __future__ import annotations

import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version
from pathlib import Path

import dask
import lsdb
import nested_pandas as npd
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.fs as pafs
import pyarrow.parquet as pq
from upath import UPath

from ibench import Run, capture, metric
from ibench_storage.profiles import target
from ibench_storage.store import Store

RANGE = 64 << 20
VARIANTS = ("pa_arrow", "pa_pandas_numpy", "pa_pandas_arrow", "npd_direct", "lsdb", "pa_arrow_native", "pa_arrow_ranges")
S3_ONLY = ("pa_arrow_native", "pa_arrow_ranges")


class Wire:
    n = 0
    lock = threading.Lock()


def _add(n: int) -> None:
    with Wire.lock:
        Wire.n += n


def _count_s3_bytes() -> None:
    """Count payload bytes at the s3fs level: ranged reads of file objects and the planned ranges of fsspec.parquet."""
    import s3fs

    if getattr(s3fs.core.S3File._fetch_range, "_counted", False):
        return
    fetch, cat = s3fs.core.S3File._fetch_range, s3fs.S3FileSystem._cat_file

    def counted_fetch(self, start, end):
        b = fetch(self, start, end)
        _add(len(b))
        return b

    async def counted_cat(self, *args, **kwargs):
        b = await cat(self, *args, **kwargs)
        _add(len(b))
        return b

    counted_fetch._counted = True
    s3fs.core.S3File._fetch_range = counted_fetch
    s3fs.S3FileSystem._cat_file = counted_cat


class Source:
    """One catalog on one profile: the partitions present, their paths, and the readers that open them."""

    def __init__(self, prof: dict, spec: dict):
        self.prof = prof
        self.catalog = spec["catalog"].strip("/")
        self.column = spec["column"]
        self.cols = [self.column, "ra", "dec", "_healpix_29"]
        self.s3 = prof["kind"] == "s3"
        self.store = Store(prof)
        if self.s3:
            self._init_s3(spec.get("pool", 64))
        else:
            self.root, self.fs, self.nfs, self.opts = Path(prof["root"]), None, None, {}
        self.pixels, self.keys = self._select(spec.get("offset", 0), spec.get("partitions", 0))
        with ThreadPoolExecutor(8) as ex:
            self.need = sum(ex.map(self._need, self.keys))

    def _init_s3(self, pool: int) -> None:
        import s3fs

        prof = self.prof
        if "," in prof["endpoint"]:
            raise SystemExit("hats reads use one endpoint: set IBENCH_S3_ENDPOINT to a single URL")
        key, secret = os.environ.get("AWS_ACCESS_KEY_ID"), os.environ.get("AWS_SECRET_ACCESS_KEY")
        if not (key and secret):
            raise SystemExit("set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        virtual = prof.get("lookup") == "host"
        region = prof.get("region") or "us-east-1"
        self.bucket = prof["bucket"]
        self.opts = dict(
            key=key, secret=secret, endpoint_url=prof["endpoint"], client_kwargs={"region_name": region},
            config_kwargs={"s3": {"addressing_style": "virtual" if virtual else "path"}, "max_pool_connections": pool})
        self.fs = s3fs.S3FileSystem(**self.opts)
        scheme, host = prof["endpoint"].split("://")
        self.nfs = pafs.S3FileSystem(access_key=key, secret_key=secret, endpoint_override=host, scheme=scheme,
                                     region=region, force_virtual_addressing=virtual)
        _count_s3_bytes()

    def path(self, key: str) -> str:
        return f"{self.bucket}/{key}" if self.s3 else str(self.root / key)

    def upath(self, key: str) -> UPath:
        return UPath(f"s3://{self.bucket}/{key}", **self.opts) if self.s3 else UPath(str(self.root / key))

    def _select(self, offset: int, count: int) -> tuple[list[tuple[int, int]], list[str]]:
        """Catalog partitions that exist under the target, in pixel order, then offset and count applied."""
        found = {k for k, _ in self.store.list(f"{self.catalog}/dataset/")}
        pixels, keys = [], []
        for p in lsdb.open_catalog(self.upath(self.catalog)).get_healpix_pixels():
            key = f"{self.catalog}/dataset/Norder={p.order}/Dir={(p.pixel // 10000) * 10000}/Npix={p.pixel}.parquet"
            if key in found:
                pixels.append((p.order, p.pixel))
                keys.append(key)
        pixels, keys = pixels[offset:], keys[offset:]
        if count > 0:
            pixels, keys = pixels[:count], keys[:count]
        if not keys:
            raise SystemExit(f"no partitions of {self.catalog!r} found on {target(self.prof)}")
        return pixels, keys

    def _need(self, key: str) -> int:
        """Compressed bytes of the four columns: what any reader has to fetch."""
        with (self.fs.open(self.path(key), "rb") if self.fs else open(self.path(key), "rb")) as f:
            md = pq.ParquetFile(f).metadata
        return sum(md.row_group(i).column(j).total_compressed_size
                   for i in range(md.num_row_groups) for j in range(md.num_columns)
                   if md.row_group(i).column(j).path_in_schema in self.cols)


def _mean(parts) -> float:
    tot, cnt = 0.0, 0
    for s, c in parts:
        tot += s
        cnt += c
    return tot / cnt


def _variants(src: Source, threads: int) -> dict:
    column, cols = src.column, src.cols

    def pool(fn):
        with ThreadPoolExecutor(threads) as ex:
            return _mean(ex.map(fn, src.keys))

    def table(k, fs):
        return pq.read_table(src.path(k), columns=cols, use_threads=False, filesystem=fs)

    def pa_arrow():
        def one(k):
            c = table(k, src.fs).column(column)
            return (pc.sum(c).as_py() or 0.0), pc.count(c, mode="only_valid").as_py()
        return pool(one)

    def pa_pandas_numpy():
        def one(k):
            c = table(k, src.fs).to_pandas()[column]
            return float(c.sum()), int(c.count())
        return pool(one)

    def pa_pandas_arrow():
        def one(k):
            c = table(k, src.fs).to_pandas(types_mapper=pd.ArrowDtype)[column]
            return float(c.sum()), int(c.count())
        return pool(one)

    def npd_direct():
        def one(k):
            c = npd.read_parquet(src.upath(k), columns=cols)[column]
            return float(c.sum()), int(c.count())
        return pool(one)

    def lsdb_compute():
        cat = lsdb.open_catalog(src.upath(src.catalog), columns=[column], search_filter=lsdb.PixelSearch(src.pixels))

        def part_mean(df, target_column=""):
            c = df[target_column]
            return pd.DataFrame([{"s": float(c.sum()), "n": int(c.count())}])

        meta = pd.DataFrame({"s": pd.Series(dtype="float64"), "n": pd.Series(dtype="int64")})
        with dask.config.set({"num_workers": threads}):
            res = cat.map_partitions(part_mean, target_column=column, meta=meta).compute(progress_bar=False)
        return float(res["s"].sum()) / int(res["n"].sum())

    def pa_arrow_native():
        def one(k):
            c = table(k, src.nfs).column(column)
            return (pc.sum(c).as_py() or 0.0), pc.count(c, mode="only_valid").as_py()
        return pool(one)

    def pa_arrow_ranges():
        from fsspec.parquet import open_parquet_file

        def one(k):
            with open_parquet_file(src.path(k), columns=cols, engine="pyarrow", fs=src.fs) as f:
                c = pq.read_table(f, columns=cols, use_threads=False).column(column)
            return (pc.sum(c).as_py() or 0.0), pc.count(c, mode="only_valid").as_py()
        return pool(one)

    out = {"pa_arrow": pa_arrow, "pa_pandas_numpy": pa_pandas_numpy, "pa_pandas_arrow": pa_pandas_arrow,
           "npd_direct": npd_direct, "lsdb": lsdb_compute}
    if src.s3:
        out["pa_arrow_native"] = pa_arrow_native
        out["pa_arrow_ranges"] = pa_arrow_ranges
    return out


def _env(prof: dict, name: str) -> dict:
    libs = {p: version(p) for p in ("lsdb", "hats", "nested-pandas", "pyarrow", "s3fs", "dask")}
    return {**capture(prof.get("root")), "libs": libs, "tool": {"name": name, "version": libs["lsdb"], "cmd": sys.argv}}


def _params(src: Source, spec: dict, **extra) -> dict:
    base = {"catalog": src.catalog, "column": src.column, "partitions": len(src.keys), "offset": spec.get("offset", 0)}
    if src.s3:
        base |= {"endpoint": src.prof["endpoint"], "lookup": src.prof.get("lookup"), "pool": spec.get("pool", 64)}
    return base | extra


def _tags(src: Source) -> dict:
    return {"target": f"{target(src.prof)}/{src.catalog}"}


def reads(src: Source, spec: dict, threads: int, suffix: str, scenario: str) -> list[Run]:
    run_all = _variants(src, threads)
    names = [v for v in spec.get("variants", VARIANTS) if v in run_all]
    pa.set_cpu_count(threads)
    if spec.get("warm", True):
        for v in names:
            run_all[v]()
    out, means = [], {}
    for v in names:
        Wire.n = 0
        t0 = time.perf_counter()
        val = run_all[v]()
        wall = time.perf_counter() - t0
        wire = Wire.n
        means[v] = val
        m = {"wall_s": wall, "need_mb": src.need / 1e6, "mean": val}
        if src.s3 and v != "pa_arrow_native":
            m |= {"wire_mb": wire / 1e6, "over_read": wire / src.need}
        gbps = src.need * 8 / wall / 1e9
        out.append(Run("storage", f"hats.{v}.n{len(src.keys)}{suffix}", metric("gbps", gbps, "Gbps"),
                       {"gbps": gbps, **m}, _params(src, spec, threads=threads, variant=v, warm=spec.get("warm", True)),
                       scenario, src.prof["name"], env=_env(src.prof, v), duration_s=wall, tags=_tags(src)))
    if len({round(x, 6) for x in means.values()}) > 1:
        raise SystemExit(f"readers disagree on the mean of {src.column}: {means}")
    return out


def stat_latency(src: Source, scenario: str, count: int = 20) -> Run:
    """Time to learn one partition's size: S3 HEAD or POSIX stat, one at a time."""
    times = []
    for k in src.keys[:count]:
        t0 = time.perf_counter()
        if src.s3:
            src.store.clients[0].head_object(Bucket=src.bucket, Key=k)
        else:
            os.stat(src.path(k))
        times.append((time.perf_counter() - t0) * 1e3)
    times.sort()
    p50, mx = times[len(times) // 2], times[-1]
    return Run("storage", "hats.stat", metric("p50_ms", p50, "ms", higher_is_better=False),
               {"p50_ms": p50, "max_ms": mx}, _params(src, {}, samples=len(times)), scenario, src.prof["name"],
               env=_env(src.prof, "head" if src.s3 else "stat"), tags=_tags(src))


def ceiling(src: Source, spec: dict, threads: int, scenario: str) -> Run:
    """Parallel ranged reads of whole partitions, no decoding: what this client can pull at all."""
    keys = [src.keys[i % len(src.keys)] for i in range(threads * 2)]

    def one(k):
        if src.s3:
            return len(src.fs.cat_file(src.path(k), start=0, end=RANGE))
        with open(src.path(k), "rb") as f:
            return len(f.read(RANGE))

    t0 = time.perf_counter()
    with ThreadPoolExecutor(threads) as ex:
        total = sum(ex.map(one, keys))
    wall = time.perf_counter() - t0
    gbps = total * 8 / wall / 1e9
    return Run("storage", f"hats.ceiling.t{threads}", metric("gbps", gbps, "Gbps"),
               {"gbps": gbps, "wall_s": wall, "gb": total / 1e9}, _params(src, spec, threads=threads, range_mib=RANGE >> 20),
               scenario, src.prof["name"], env=_env(src.prof, "range-read"), duration_s=wall, tags=_tags(src))


def run(prof: dict, spec: dict, scenario: str) -> list[Run]:
    if bad := [v for v in spec.get("variants", ()) if v not in VARIANTS]:
        raise SystemExit(f"unknown variant {', '.join(bad)}; available: {', '.join(VARIANTS)}")
    src = Source(prof, spec)
    levels = spec["threads"] if isinstance(spec.get("threads"), list) else [spec.get("threads", 8)]
    out = [stat_latency(src, scenario)]
    for t in levels:
        out += reads(src, spec, t, f".t{t}" if len(levels) > 1 else "", scenario)
    out += [ceiling(src, spec, t, scenario) for t in spec.get("ceiling", [])]
    return out
