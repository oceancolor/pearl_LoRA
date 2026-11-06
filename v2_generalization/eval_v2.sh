#!/usr/bin/env bash
# 训练后对比评估：用同一组 OOD prompts 给指定 LoRA 出图
# 用法: bash eval_v2.sh <lora.safetensors> <tag> [mul] [prompts_file]
set -euo pipefail
B=/root/workspace/benjamin
NT=$B/next_train
LORA=${1:?need lora path}
TAG=${2:?need tag}
MUL=${3:-1.0}
PROMPTS=${4:-$NT/ood_prompts_v2.txt}
OUT=$NT/eval_out/v2_compare/$TAG
mkdir -p "$OUT"

export HF_HOME=$B/cache/hf HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TMPDIR=/tmp
export LD_LIBRARY_PATH=/usr/local/cuda-12.1/nsight-systems-2023.1.2/host-linux-x64/Mesa:${LD_LIBRARY_PATH:-}

"$B/venv/bin/python" "$B/sd-scripts/sdxl_gen_img.py" \
  --ckpt "$B/models/sd_xl_base_1.0.safetensors" \
  --network_module networks.lora --network_weights "$LORA" \
  --network_mul "$MUL" --from_file "$PROMPTS" \
  --W 896 --H 896 --steps 28 --sampler euler_a --seed 20261106 \
  --images_per_prompt 1 --outdir "$OUT" --sdpa
echo "[eval_v2] done -> $OUT"
