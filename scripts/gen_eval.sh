#!/usr/bin/env bash
# gen_eval.sh — 用训练好的 LoRA 出 SPEC §9 评估图（4 条 branch × N 张）。
#
# 与训练中采样的区别（很重要）：
#   - 训练中采样用 LoRA 权重 1.0，会放大 LoRA 的一切倾向（含缺点）
#   - 正式评估按 SPEC §7 生成期拼法，权重 0.8
#   - 必须 --no_half_vae：SDXL 的 VAE 在 fp16 下溢出，采样图会全黑（本机实测）
#
# 用法：
#   bash scripts/gen_eval.sh
#   LORA=~/pearl_LoRA/output/lora/decomineral_v1_16gb.safetensors N=8 bash scripts/gen_eval.sh
set -euo pipefail

PRJ="${PROJECT_DIR:-$HOME/pearl_LoRA}"
SD="${SD_SCRIPTS:-$HOME/sd-scripts}"
CKPT="${CKPT:-$PRJ/models/sd_xl_base_1.0.safetensors}"
LORA="${LORA:-$PRJ/output/lora/decomineral_v1_16gb.safetensors}"
MUL="${MUL:-0.8}"
N="${N:-8}"
STEPS="${STEPS:-28}"
SCALE="${SCALE:-7.0}"
SEED="${SEED:-20260915}"
W="${W:-1024}"
H="${H:-1024}"
OUT="${OUT:-$PRJ/eval_out}"

# 风格锁：永远同一句（SPEC §7），与 prompts/generate_en.yaml 一致
STYLE="decomineral style, flat mineral pigments, no chiaroscuro, pattern equal to form, tapestry space, jewel-like palette, closed color shapes, ornamental border"
NEG="photograph, realistic lighting, chiaroscuro, 3d render, anime, oil painting, western perspective, watermark, text, artist name"
PAL="malachite, azurite, cinnabar, gold"

[ -f "$CKPT" ] || { echo "未找到 SDXL base: $CKPT"; exit 1; }
[ -f "$LORA" ] || { echo "未找到 LoRA: $LORA"; exit 1; }

gen() {  # gen <branch> <subject>
  local branch="$1" subject="$2"
  echo "== $branch =="
  python "$SD/sdxl_gen_img.py" \
    --ckpt "$CKPT" \
    --network_module networks.lora --network_weights "$LORA" --network_mul "$MUL" \
    --prompt "$STYLE, $subject, $PAL" \
    --negative "$NEG" \
    --images_per_prompt "$N" --steps "$STEPS" --scale "$SCALE" --seed "$SEED" \
    --W "$W" --H "$H" --fp16 --no_half_vae \
    --outdir "$OUT/$branch"
}

gen ritual "a ceremonial hall with canopy, attendants, sacred tree and geometric pavement, ritual but not a copy of a known cave"
gen court  "a vast stone palace of blue and green masonry with arcades and lattice windows, a city of countless stairs in silhouette behind it with a jade glow, a winding procession road with banners, instruments, horses and animals, curling floating textiles, and a throne spreading like a peacock tail, lit against the dark hall"
gen water  "an underwater palace, fish-scale waves, lotus as fabric, boats and palaces stacked like a tapestry"
gen future "an orbital palace and procession of machine-bodied attendants, towers like sutra pillars, sky-boats treated as ornament not sci-fi chrome"

echo "----------------------------"
echo "完成：$OUT"
find "$OUT" -name "*.png" | wc -l
