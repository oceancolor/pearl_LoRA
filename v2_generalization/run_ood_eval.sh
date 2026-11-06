#!/usr/bin/env bash
# OOD 评估：量化当前 LoRA 的"无条件装饰画泄漏"与主体可控性
# 三组对比：base / 风格LoRA@1.0 / 风格LoRA@0.6（可选概念LoRA）
# 用法: bash /root/workspace/benjamin/next_train/run_ood_eval.sh [outdir]
set -euo pipefail
B=/root/workspace/benjamin
NT=$B/next_train
OUT=${1:-$NT/eval_out/run_$(date +%Y%m%d_%H%M)}
mkdir -p "$OUT"

BASE=$B/models/sd_xl_base_1.0.safetensors
STYLE=$B/final_loras/decomineral_v1_16gb.safetensors

# tokenizer/CLIP 全部走项目本地缓存，不联网
export HF_HOME=$B/cache/hf
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TMPDIR=$B/tmp

# 需要时放开注释加概念组
# CONCEPT=$B/last_lora/deco_ritual.safetensors

run() { # <name> <mul|none> <weights|none>
  local name=$1 mul=$2 weights=$3
  echo "[eval] $name"
  if [ "$weights" = "none" ]; then
    "$B/venv/bin/python" "$B/sd-scripts/sdxl_gen_img.py" \
      --ckpt "$BASE" --from_file "$NT/ood_prompts.txt" \
      --W 896 --H 896 --steps 28 --sampler euler_a --seed 20261106 \
      --images_per_prompt 1 --outdir "$OUT/$name" --sdpa
  else
    "$B/venv/bin/python" "$B/sd-scripts/sdxl_gen_img.py" \
      --ckpt "$BASE" --network_module networks.lora --network_weights "$weights" \
      --network_mul "$mul" --from_file "$NT/ood_prompts.txt" \
      --W 896 --H 896 --steps 28 --sampler euler_a --seed 20261106 \
      --images_per_prompt 1 --outdir "$OUT/$name" --sdpa
  fi
}

run base      none none
run style100  1.0  "$STYLE"
run style060  0.6  "$STYLE"
# run ritual100 1.0  "$CONCEPT"

echo "[eval] done -> $OUT"
