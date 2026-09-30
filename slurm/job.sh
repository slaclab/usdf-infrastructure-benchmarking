#!/usr/bin/env bash
# Run any ibench command as a batch job; arguments are the command.
#   sbatch slurm/job.sh ibench-storage run s3-remote-read --profile s3
# Other site or shape: sbatch -p <partition> -A <account> --cpus-per-task=32 --mem=128G slurm/job.sh ...
#SBATCH --job-name=ibench
#SBATCH --partition=hopper
#SBATCH --account=rubin:developers
#SBATCH --qos=normal
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=04:00:00
#SBATCH --output=slurm-%x-%j.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-.}"
exec uv run "$@"
