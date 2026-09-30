"""One read interface over POSIX files and S3 objects."""
from __future__ import annotations

import itertools
import os
from contextlib import closing
from pathlib import Path

CHUNK = 8 << 20


class Posix:
    def __init__(self, root: str):
        self.root = Path(root)

    def size(self, key: str) -> int:
        return (self.root / key).stat().st_size

    def list(self, prefix: str) -> list[tuple[str, int]]:
        files = (p for p in (self.root / prefix).rglob("*") if p.is_file())
        return sorted((str(p.relative_to(self.root)), p.stat().st_size) for p in files)

    def read(self, key: str, offset: int, length: int) -> int:
        fd = os.open(self.root / key, os.O_RDONLY)
        try:
            n = 0
            while n < length:
                chunk = os.pread(fd, min(CHUNK, length - n), offset + n)
                if not chunk:
                    break
                n += len(chunk)
            return n
        finally:
            os.close(fd)


class S3:
    """S3 reads; several comma-separated endpoints are used round-robin (one client each)."""

    def __init__(self, endpoint: str, bucket: str, region: str | None = None, anonymous: bool = False, pool: int = 256):
        import boto3
        from botocore import UNSIGNED
        from botocore.config import Config

        self.bucket = bucket
        cfg = Config(max_pool_connections=pool, retries={"max_attempts": 3},
                     signature_version=UNSIGNED if anonymous else None)
        self.clients = [boto3.client("s3", endpoint_url=e.strip(), region_name=region, config=cfg)
                        for e in endpoint.split(",")]
        self._next = itertools.count()

    def _client(self):
        return self.clients[next(self._next) % len(self.clients)]

    def size(self, key: str) -> int:
        return self.clients[0].head_object(Bucket=self.bucket, Key=key)["ContentLength"]

    def list(self, prefix: str) -> list[tuple[str, int]]:
        pages = self.clients[0].get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=prefix)
        return [(o["Key"], o["Size"]) for page in pages for o in page.get("Contents", [])]

    def read(self, key: str, offset: int, length: int) -> int:
        resp = self._client().get_object(Bucket=self.bucket, Key=key, Range=f"bytes={offset}-{offset + length - 1}")
        with closing(resp["Body"]) as body:
            return sum(len(c) for c in body.iter_chunks(1 << 20))
