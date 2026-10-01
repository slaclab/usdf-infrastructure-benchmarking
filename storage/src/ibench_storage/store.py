"""List, read and write objects over a POSIX root or an S3 bucket (mock data and the tokenization workload)."""
from __future__ import annotations

import itertools
import shutil
from pathlib import Path

CHUNK = 8 << 20


class Store:
    def __init__(self, prof: dict):
        self.posix = prof["kind"] == "posix"
        if self.posix:
            self.root = Path(prof["root"])
            return
        import boto3
        from botocore.config import Config

        style = "virtual" if prof.get("lookup") == "host" else "path"
        cfg = Config(max_pool_connections=64, retries={"max_attempts": 3}, s3={"addressing_style": style})
        self.bucket = prof["bucket"]
        self.clients = [boto3.client("s3", endpoint_url=e.strip(), region_name=prof.get("region"), config=cfg)
                        for e in prof["endpoint"].split(",")]
        self._next = itertools.count()

    def _client(self):
        return self.clients[next(self._next) % len(self.clients)]

    def list(self, prefix: str, limit: int | None = None) -> list[tuple[str, int]]:
        if self.posix:
            files = (p for p in (self.root / prefix).rglob("*") if p.is_file())
            out = sorted((str(p.relative_to(self.root)), p.stat().st_size) for p in files)
            return out[:limit]
        out = []
        for page in self.clients[0].get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefix):
            out += [(o["Key"], o["Size"]) for o in page.get("Contents", [])]
            if limit and len(out) >= limit:
                break
        return out[:limit]

    def read(self, key: str) -> bytes:
        if self.posix:
            return (self.root / key).read_bytes()
        return self._client().get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def write(self, key: str, stream) -> None:
        if self.posix:
            path = self.root / key
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("wb") as f:
                shutil.copyfileobj(stream, f, CHUNK)
            return
        from boto3.s3.transfer import TransferConfig

        self._client().upload_fileobj(stream, self.bucket, key,
                                      Config=TransferConfig(multipart_chunksize=16 << 20, max_concurrency=4))

    def delete(self, keys: list[str]) -> None:
        if self.posix:
            for k in keys:
                (self.root / k).unlink(missing_ok=True)
            return
        for i in range(0, len(keys), 1000):
            self._client().delete_objects(Bucket=self.bucket,
                                          Delete={"Objects": [{"Key": k} for k in keys[i:i + 1000]]})
