"""Tokenization workload: read text shards, tokenize, write token shards; reports throughput and the I/O share."""
from __future__ import annotations

import array
import io
import json
import multiprocessing as mp
import os
import time
from pathlib import Path

from ibench import Run, capture, metric
from ibench.env import cpus
from ibench_storage.engine import RAW
from ibench_storage.profiles import target
from ibench_storage.store import Store


def _tiny_tokenizer(sample: list[str], path: Path) -> None:
    from tokenizers import Tokenizer, models, pre_tokenizers, trainers

    tok = Tokenizer(models.BPE(unk_token="[UNK]"))
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    tok.train_from_iterator(sample, trainers.BpeTrainer(vocab_size=8000, special_tokens=["[UNK]"]))
    tok.save(str(path))


def _texts(raw: bytes) -> list[str]:
    out = []
    for line in raw.decode(errors="ignore").splitlines():
        try:
            out.append(json.loads(line)["text"])
        except (ValueError, KeyError):
            pass  # truncated last line
    return out


def _worker(args: tuple) -> dict:
    prof, keys, out_base, batch, tok_path = args
    from tokenizers import Tokenizer

    store, tok = Store(prof), Tokenizer.from_file(tok_path)
    c = dict(io_s=0.0, cpu_s=0.0, docs=0, tokens=0, read=0, written=0, outputs=[])
    for key in keys:
        t = time.perf_counter()
        raw = store.read(key)
        c["io_s"] += time.perf_counter() - t
        t = time.perf_counter()
        texts, ids = _texts(raw), array.array("I")
        for i in range(0, len(texts), batch):
            for enc in tok.encode_batch(texts[i:i + batch]):
                ids.extend(enc.ids)
        c["cpu_s"] += time.perf_counter() - t
        out, name = ids.tobytes(), f"{out_base}/{Path(key).stem}.bin"
        t = time.perf_counter()
        store.write(name, io.BytesIO(out))
        c["io_s"] += time.perf_counter() - t
        c["docs"] += len(texts)
        c["tokens"] += len(ids)
        c["read"] += len(raw)
        c["written"] += len(out)
        c["outputs"].append(name)
    return c


def run(prof: dict, spec: dict, scenario: str, base: str, workers: int | None = None, keep: bool = False) -> Run:
    """Every worker process tokenizes whole shards; outputs go under <base>/tokenized/<time> and are removed
    unless keep. The tokenizer is a small BPE trained on the first shard unless spec['tokenizer'] names a file."""
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    store = Store(prof)
    shards = [k for k, _ in store.list(f"{base}/{spec['data']}/", spec.get("max_shards"))]
    if not shards:
        raise SystemExit(f"no shards under {base}/{spec['data']}/; run `ibench-storage mkdata` first")
    workers = min(workers or spec.get("workers") or cpus(), len(shards))
    RAW.mkdir(parents=True, exist_ok=True)
    tok_path = spec.get("tokenizer") or str(RAW / "tokenizer.json")
    if not spec.get("tokenizer"):
        _tiny_tokenizer(_texts(store.read(shards[0]))[:5000], Path(tok_path))
    out_base = f"{base}/tokenized/{int(time.time())}"
    jobs = [(prof, shards[i::workers], out_base, spec.get("batch_size", 1000), tok_path) for i in range(workers)]
    t0 = time.time()
    with mp.get_context("spawn").Pool(workers) as pool:
        parts = pool.map(_worker, jobs)
    wall = time.time() - t0
    if not keep:
        store.delete([o for p in parts for o in p["outputs"]])
    tot = {k: sum(p[k] for p in parts) for k in ("io_s", "cpu_s", "docs", "tokens", "read", "written")}
    metrics = {"docs_per_s": tot["docs"] / wall, "read_mbps": tot["read"] / wall / 1e6,
               "write_mbps": tot["written"] / wall / 1e6, "io_share": tot["io_s"] / (tot["io_s"] + tot["cpu_s"]),
               "shards": len(shards), "workers": workers, "docs": tot["docs"], "tokens": tot["tokens"], "wall_s": wall}
    return Run("storage", f"tokenize.{spec.get('label', spec['data'])}",
               metric("tokens_per_s", tot["tokens"] / wall, "tok/s"), metrics, {**spec, "workers": workers}, scenario,
               prof["name"], env=capture(prof.get("root")), duration_s=wall, tags={"target": target(prof)})
