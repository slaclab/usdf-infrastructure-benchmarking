#!/usr/bin/env bash
# Install the read-benchmark tools: warp (S3 profiles, built with Go) and check fio (POSIX profiles).
# No Go? Download a warp release binary from https://github.com/minio/warp/releases and put it on PATH.
set -euo pipefail

WARP_VERSION="${WARP_VERSION:-v1.8.2}"

if ! command -v warp >/dev/null; then
  command -v go >/dev/null || { echo "warp and go not found; see the note at the top of this script" >&2; exit 1; }
  GOBIN="${GOBIN:-$HOME/.local/bin}" go install "github.com/minio/warp@${WARP_VERSION}"
  echo "installed warp ${WARP_VERSION} into ${GOBIN:-$HOME/.local/bin}; put it on PATH if needed"
fi
command -v warp >/dev/null && warp --version || true
command -v fio >/dev/null && fio --version || echo "warning: fio not found (needed for POSIX profiles)" >&2
