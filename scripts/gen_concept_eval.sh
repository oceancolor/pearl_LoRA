#!/usr/bin/env bash
# gen_concept_eval.sh — 概念 LoRA 出图：风格 LoRA + 概念 LoRA 叠加（按 SPEC §7 生成期拼法）。
#
# 与 gen_eval.sh 的区别：
#   - 叠两个 LoRA（kohya 的 --lora_weights 支持逗号分隔多个 "路径;权重"）
#   - 每支概念用各自的 subject
#   - 可选 MODE=concept_only 只挂概念 LoRA，用来看触发词本身绑定了什么（不掺风格干扰）
#
# 用法：
#   bash scripts/gen_concept_eval.sh ritual            # 风格0.6 + 概念0.7，4 张
#   N=8 bash scripts/gen_concept_eval.sh water         # 8 张
#   MODE=concept_only bash scripts/gen_concept_eval.sh future_seed
set -euo pipefail

SLUG="${1:-}"
if [[ -z "$SLUG" ]]; then
  echo "用法: bash scripts/gen_concept_eval.sh ritual|water|future_seed"
  exit 2
fi

# 本机的 python 只装在 venv 里，没激活时会「python: command not found」（2026-10-28 实测）
if ! command -v python >/dev/null 2>&1 && [[ -f "$HOME/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$HOME/venv/bin/activate"
  echo "已激活 venv: $(command -v python)"
fi
command -v python >/dev/null 2>&1 || { echo "找不到 python，先 source ~/venv/bin/activate"; exit 1; }

PRJ="${PROJECT_DIR:-$HOME/pearl_LoRA}"
SD="${SD_SCRIPTS:-$HOME/sd-scripts}"
CKPT="${CKPT:-$PRJ/models/sd_xl_base_1.0.safetensors}"
STYLE_LORA="${STYLE_LORA:-$PRJ/output/lora/decomineral_v1_16gb.safetensors}"
MUL_STYLE="${MUL_STYLE:-0.6}"     # 与 gen_eval.sh 一致（0.8 会出伪书法）
MUL_CONCEPT="${MUL_CONCEPT:-0.7}"
N="${N:-4}"
BASE_SEED="${BASE_SEED:-20261028}"
STEPS="${STEPS:-28}"
MODE="${MODE:-both}"
OUT="${OUT:-$PRJ/eval_concept/$SLUG}"

case "$SLUG" in
  ritual)      TRIG=deco_ritual
               SUBJ="a ceremonial hall in a dense night grove under a full moon, a deity on a lotus throne beneath a canopy of dark leaves, rows of attendants with banners, a lotus pond, patterned ground" ;;
  water)       TRIG=deco_water
               SUBJ="a full moon over a wide bay, pine-covered islets and small boats on patterned water, a night river with willows and a jetty" ;;
  future_seed) TRIG=deco_future
               SUBJ="a floating palace among clouds and stars above a dark forest, a winged spirit rising over a moonlit jungle, towers like sutra pillars treated as ornament" ;;
  *) echo "未知概念: $SLUG"; exit 2 ;;
esac

CONCEPT_LORA="$PRJ/output/lora/$TRIG.safetensors"

STYLE="decomineral style, flat mineral pigments, no chiaroscuro, pattern equal to form, tapestry space, jewel-like palette, closed color shapes, ornamental border"
NEG="photograph, realistic lighting, chiaroscuro, 3d render, anime, oil painting, western perspective, watermark, text, artist name, signature"
PAL="malachite, azurite, cinnabar, gold"

[ -f "$CKPT" ] || { echo "未找到 SDXL base: $CKPT"; exit 1; }
[ -f "$CONCEPT_LORA" ] || { echo "未找到概念 LoRA: $CONCEPT_LORA"; exit 1; }

echo "== 风格 LoRA 校验（10-10 好版应为 6d4af5c7；9edebbfc 是 10-09 坏版）=="
if [ -f "$STYLE_LORA" ]; then
  H=$(sha256sum "$STYLE_LORA" | cut -c1-8)
  echo "  $H  $STYLE_LORA"
  [ "$H" = "9edebbfc" ] && { echo "  !! 这是 10-09 坏版（出黑图），别用"; exit 1; }
  [ "$H" = "6d4af5c7" ] || echo "  !! 哈希不在已知基准内，请确认来源"
else
  echo "  !! 缺风格 LoRA: $STYLE_LORA"
  [ "$MODE" = "concept_only" ] || exit 1
fi

case "$MODE" in
  both)         LORAS="$STYLE_LORA;$MUL_STYLE,$CONCEPT_LORA;$MUL_CONCEPT" ;;
  concept_only) LORAS="$CONCEPT_LORA;$MUL_CONCEPT" ;;
  *) echo "MODE 只支持 both / concept_only"; exit 2 ;;
esac

INFER="$PRJ/.gen_concept_infer.py"
cp "$SD/sdxl_minimal_inference.py" "$INFER"
sed -i 's/^    steps = 50/    steps = '"$STEPS"'/' "$INFER"
sed -i 's/^    seed = None.*/    seed = int(os.environ.get("GEN_SEED", "'"$BASE_SEED"'"))/' "$INFER"
sed -i 's/^\([[:space:]]*\).*set_use_memory_efficient_attention_xformers.*/\1pass  # xformers 未安装，已禁用/' "$INFER"
sed -i 's/set_use_memory_efficient_attention(True/set_use_memory_efficient_attention(False/g' "$INFER"

# concept_only 时不加风格锁词（否则等于用提示词硬凑风格，看不出概念 LoRA 自己学到了什么）
if [ "$MODE" = "concept_only" ]; then PROMPT="$TRIG, $SUBJ"; else PROMPT="$STYLE, $TRIG, $SUBJ, $PAL"; fi

mkdir -p "$OUT"
echo "== 生成（mode=$MODE, steps=$STEPS, style=$MUL_STYLE, concept=$MUL_CONCEPT, n=$N）=="
echo "   prompt: ${PROMPT:0:110}..."
# ★推理脚本 import 了 kohya 的 networks.lora，必须把 sd-scripts 加进 PYTHONPATH
# （脚本被拷到项目目录运行，否则报 ModuleNotFoundError: No module named 'networks'）
export PYTHONPATH="$SD${PYTHONPATH:+:$PYTHONPATH}"

for ((i=0; i<N; i++)); do
  GEN_SEED=$((BASE_SEED + i)) python "$INFER" \
    --ckpt_path "$CKPT" \
    --lora_weights "$LORAS" \
    --prompt "$PROMPT" \
    --negative_prompt "$NEG" \
    --output_dir "$OUT"
done

echo "完成：$OUT （$(find "$OUT" -name '*.png' | wc -l) 张）"
