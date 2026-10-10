#!/usr/bin/env bash
# gen_eval.sh — 用训练好的 LoRA 出 SPEC §9 评估图（4 条 branch × N 张）。
#
# 为什么用 kohya 的 sdxl_minimal_inference.py 而不是训练中采样：
#   - 训练中采样 LoRA 权重是 1.0，会放大 LoRA 的一切倾向（含缺点）
#   - 正式评估按 SPEC §7 生成期拼法，权重 0.8（--lora_weights "路径;0.8"）
#   - 该脚本内置「fp16 时 VAE 转 fp32」，规避 SDXL fp16 出黑图的已知问题
#     （kohya 源码注释：NaN seems to be more likely to occur in fp16）
#
# 该脚本内置的 steps=50 / seed=None 与 prompts/eval_grid.txt 的约定
# （28 步 / seed 20260915）不符，故本脚本会拷一份出来改这两处。
# 8 张图若用同一个 seed 会完全相同，因此种子按 20260915 + i 递增。
#
# 用法：
#   bash scripts/gen_eval.sh            # 4 branch × 8 张
#   N=2 bash scripts/gen_eval.sh        # 先看个大概
set -euo pipefail

PRJ="${PROJECT_DIR:-$HOME/pearl_LoRA}"
SD="${SD_SCRIPTS:-$HOME/sd-scripts}"
CKPT="${CKPT:-$PRJ/models/sd_xl_base_1.0.safetensors}"
LORA="${LORA:-$PRJ/output/lora/decomineral_v1_16gb.safetensors}"
MUL="${MUL:-0.8}"
N="${N:-8}"
BASE_SEED="${BASE_SEED:-20260915}"
STEPS="${STEPS:-28}"
OUT="${OUT:-$PRJ/eval_out}"

STYLE="decomineral style, flat mineral pigments, no chiaroscuro, pattern equal to form, tapestry space, jewel-like palette, closed color shapes, ornamental border"
NEG="photograph, realistic lighting, chiaroscuro, 3d render, anime, oil painting, western perspective, watermark, text, artist name"
PAL="malachite, azurite, cinnabar, gold"

[ -f "$CKPT" ] || { echo "未找到 SDXL base: $CKPT"; exit 1; }
[ -f "$LORA" ] || { echo "未找到 LoRA: $LORA"; exit 1; }

# 拷一份出来改 steps / seed（不改 kohya 原始文件）
INFER="$PRJ/.gen_eval_infer.py"
cp "$SD/sdxl_minimal_inference.py" "$INFER"
sed -i 's/^    steps = 50/    steps = '"$STEPS"'/' "$INFER"
sed -i 's/^    seed = None.*/    seed = int(os.environ.get("GEN_SEED", "'"$BASE_SEED"'"))/' "$INFER"
# 该脚本默认开启 xformers（未装会 ModuleNotFoundError，两处：
#   vae.set_use_memory_efficient_attention_xformers / unet.set_use_memory_efficient_attention(True,...)
# 一律关掉，走普通注意力）
sed -i 's/^\([[:space:]]*\).*set_use_memory_efficient_attention_xformers.*/\1pass  # xformers 未安装，已禁用/' "$INFER"
sed -i 's/set_use_memory_efficient_attention(True/set_use_memory_efficient_attention(False/g' "$INFER"
grep -n "^    steps\|^    seed\|xformers\|pass" "$INFER" | head

gen() {  # gen <branch> <subject>
  local branch="$1" subject="$2"
  mkdir -p "$OUT/$branch"
  for ((i=0; i<N; i++)); do
    GEN_SEED=$((BASE_SEED + i)) python "$INFER" \
      --ckpt_path "$CKPT" \
      --lora_weights "$LORA;$MUL" \
      --prompt "$STYLE, $subject, $PAL" \
      --negative_prompt "$NEG" \
      --output_dir "$OUT/$branch"
  done
  echo "  $branch: $(ls "$OUT/$branch" | wc -l) 张"
}

echo "== 生成评估图（steps=$STEPS, mul=$MUL, base_seed=$BASE_SEED）=="
gen ritual "a ceremonial hall with canopy, attendants, sacred tree and geometric pavement, ritual but not a copy of a known cave"
gen court  "a vast stone palace of blue and green masonry with arcades and lattice windows, a city of countless stairs in silhouette behind it with a jade glow, a winding procession road with banners, instruments, horses and animals, curling floating textiles, and a throne spreading like a peacock tail, lit against the dark hall"
gen water  "an underwater palace, fish-scale waves, lotus as fabric, boats and palaces stacked like a tapestry"
gen future "an orbital palace and procession of machine-bodied attendants, towers like sutra pillars, sky-boats treated as ornament not sci-fi chrome"

echo "----------------------------"
echo "完成：$OUT （共 $(find "$OUT" -name '*.png' | wc -l) 张）"
