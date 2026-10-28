#!/usr/bin/env bash
# 概念 LoRA 训练启动器
#   用法：bash scripts/train_concept.sh ritual|water|future_seed [--force]
#   前置：data/concept_later/<slug>/ 已备好，且 python scripts/concept_check.py 通过
#
# 做三件事：校验 -> 渲染两份 toml（含按张数算出的 num_repeats）-> 启动 kohya
set -euo pipefail

SLUG="${1:-}"
FORCE="${2:-}"
if [[ -z "$SLUG" ]]; then
  echo "用法: bash scripts/train_concept.sh ritual|water|future_seed [--force]"; exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

case "$SLUG" in
  ritual)      TRIGGER="deco_ritual" ;;
  water)       TRIGGER="deco_water" ;;
  future_seed) TRIGGER="deco_future" ;;
  *) echo "未知概念: $SLUG（只支持 ritual / water / future_seed）"; exit 2 ;;
esac

DIR="$ROOT/data/concept_later/$SLUG"
[[ -d "$DIR" ]] || { echo "缺目录: $DIR"; exit 2; }

N=$(find "$DIR" -maxdepth 1 -name '*.png' | wc -l | tr -d ' ')
echo "== $SLUG ($TRIGGER)  $N 张 =="
if (( N < 15 )); then
  echo "张数 $N < 15（SPEC §7 末要求 15–25）。补齐后再训；确要试跑加 --force。"
  [[ "$FORCE" == "--force" ]] || exit 3
fi
if (( N > 25 )); then
  echo "注意：$N > 25，建议先剔到 25 张以内再训。"
fi

# 1) 校验（除数量外的硬规则一旦 FAIL 就不许训）
python scripts/concept_check.py || {
  echo "concept_check 未通过；如仅因数量不足，可加 --force 跳过。"
  [[ "$FORCE" == "--force" ]] || exit 4
}

# 2) 渲染（1 epoch ≈ 250 步：N*repeats/grad_accum = 250）
REPEATS=$(( (250 * 4 + N - 1) / N ))
(( REPEATS < 10 )) && REPEATS=10
MODEL="${MODEL:-$ROOT/models/sd_xl_base_1.0.safetensors}"
OUTDIR="${OUTDIR:-$ROOT/output/lora}"
OUTNAME="$TRIGGER"   # 产物名用触发词，future_seed 目录对应 deco_future
LOGDIR="${LOGDIR:-$ROOT/logs}"
GEN="$ROOT/configs/_generated"
mkdir -p "$GEN" "$OUTDIR" "$LOGDIR"

DS="$GEN/dataset_concept_$SLUG.toml"
CFG="$GEN/sdxl_lora_concept_$SLUG.toml"

sed -e "s|__CONCEPT_DIR__|$DIR|" -e "s|__REPEATS__|$REPEATS|" \
    configs/dataset_concept.toml > "$DS"
sed -e "s|__MODEL__|$MODEL|" -e "s|__OUTDIR__|$OUTDIR|" \
    -e "s|__OUTNAME__|$OUTNAME|" -e "s|__LOGDIR__|$LOGDIR|" \
    configs/sdxl_lora_concept.toml > "$CFG"

echo "-- 渲染完成 --"
grep -E "image_dir|num_repeats" "$DS"
grep -E "pretrained_model|output_name|network_dim|max_train_steps" "$CFG"

# 抽检提示词：每 250 步 2 张，只带概念触发词（不叠风格 LoRA），用来看触发词是否绑定
case "$SLUG" in
  ritual)      S1="a seated deity among attendants in a dense night grove under a full moon"
               S2="a procession of worshippers beneath a canopy of dark leaves" ;;
  water)       S1="a full moon over a wide bay with small pine islands and boats"
               S2="a night river with willows and a lone boatman" ;;
  future_seed) S1="a winged spirit rising above a moonlit jungle of giant flowers"
               S2="a floating palace among clouds and stars over a dark forest" ;;
esac
NEG="photograph, 3d render, text, watermark, signature"
SAMPLE="$GEN/sample_$SLUG.txt"
{
  echo "$TRIGGER, $S1 --n $NEG --w 1024 --h 1024 --d 20260915 --s 28 --l 7"
  echo "$TRIGGER, $S2 --n $NEG --w 1024 --h 1024 --d 20261023 --s 28 --l 7"
} > "$SAMPLE"
SAMPLE_ARGS="--sample_prompts $SAMPLE --sample_every_n_steps 250 --sample_sampler euler_a --sample_at_first"

# 3) 启动（kohya 需在其目录内运行；config 用绝对路径）
SD_SCRIPTS="${SD_SCRIPTS:-$HOME/sd-scripts}"
[[ -f "$SD_SCRIPTS/sdxl_train_network.py" ]] || { echo "找不到 $SD_SCRIPTS/sdxl_train_network.py"; exit 5; }

# ★必须先删旧的 latents 缓存：cache_latents=true 会复用同目录残留的 .npz。
# 若上一轮是 fp16 且没开 no_half_vae，缓存本身就是坏的，直接导致 LoRA 报废
# （2026-10-09 首次训练就踩过，loss 看着正常、产物全废）。
find "$DIR" -name "*.npz" -delete 2>/dev/null && echo "已清理 $DIR 下的旧 latents 缓存"

echo "-- 开始训练（预计 $(python -c "print(round(1000*2.1/60))") 分钟量级）--"
cd "$SD_SCRIPTS"
python sdxl_train_network.py \
  --config_file "$CFG" \
  --dataset_config "$DS" \
  $SAMPLE_ARGS \
  ${EXTRA_ARGS:-} 2>&1 | tee "$LOGDIR/train_${SLUG}.log"
