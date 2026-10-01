# genesis/tokenization

Reads text shards, tokenizes them with [Hugging Face `tokenizers`](https://github.com/huggingface/tokenizers) in one
process per worker, and writes uint32 token shards (removed afterwards unless `--keep-output`). Reports tokens/s as
the headline plus read and write MB/s and `io_share`, the fraction of worker time spent in storage. A low
`io_share` means the run was CPU-bound and says little about storage.

```bash
uv run ibench-storage mkdata genesis/tokenization --profile s3                  # 16 GB of text shards
uv run ibench-storage tokens genesis/tokenization --profile s3 --client <label> --repeat 3
uv run ibench-storage tokens genesis/tokenization --profile posix --workers 64
```

The tokenizer is a small BPE trained on the first shard; set `tokenizer: <file>` in `scenario.yaml` to use a real one.
Output goes under `$IBENCH_DATA_PREFIX/tokenized/`, so the credential needs write access.
