#!/usr/bin/env bash
# gen_concept_eval.sh — 概念 LoRA 出图：风格 LoRA + 概念 LoRA 叠加（按 SPEC §7 生成期拼法）。
#
# 与 gen_eval.sh 的区别：
#   - 叠两个 LoRA：★这版 kohya 不支持逗号传多个，故先用 networks/merge_lora.py
#     按权重比合成一个文件再挂（2026-10-28 实测 ValueError: too many values to unpack）
#   - 每支概念用各自的 subject
#   - 可选 MODE=concept_only 只挂概念 LoRA，用来看触发词本身绑定了什么（不掺风格干扰）
#
# 用法：
#   bash scripts/gen_concept_eval.sh ritual            # 风格0.6 + 概念0.7，4 张
#   N=8 bash scripts/gen_concept_eval.sh water         # 8 张
#   MUL_STYLE=0.75 MUL_CONCEPT=0.5 OUT=~/w1 bash scripts/gen_concept_eval.sh water
#   MODE=concept_only bash scripts/gen_concept_eval.sh future_seed
set -euo pipefail

die() { echo "!! $*"; exit 1; }

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
# 2026-10-28 实测权重扫描结论：0.75 + 0.50 优于 0.60 + 0.70
#   - 0.75/0.50：装饰边框齐整、金地干净、单月、平涂稳定
#   - 0.60/0.70：概念侧过强，出现「圈月」（同心圆替代月亮）与边框不齐
MUL_STYLE="${MUL_STYLE:-0.75}"
MUL_CONCEPT="${MUL_CONCEPT:-0.50}"
N="${N:-4}"
BASE_SEED="${BASE_SEED:-20261028}"
STEPS="${STEPS:-28}"
MODE="${MODE:-both}"
OUT="${OUT:-$PRJ/eval_concept/$SLUG}"

case "$SLUG" in
  ritual)      TRIG=deco_ritual
               SUBJ="a ceremonial hall in a dense night grove beneath a single full moon high in the sky, a deity on a lotus throne beneath a canopy of dark leaves, rows of attendants with banners, a lotus pond, patterned ground" ;;
  water)       TRIG=deco_water
               SUBJ="a single full moon high in a dark sky over a wide bay, pine-covered islets and small boats on patterned water, a night river with willows and a jetty" ;;
  future_seed) TRIG=deco_future
               SUBJ="a floating palace among clouds and stars above a dark forest, a winged spirit rising over a moonlit jungle, one moon only, towers like sutra pillars treated as ornament" ;;
  *) echo "未知概念: $SLUG"; exit 2 ;;
esac

CONCEPT_LORA="$PRJ/output/lora/$TRIG.safetensors"

STYLE="decomineral style, flat mineral pigments, no chiaroscuro, pattern equal to form, tapestry space, jewel-like palette, closed color shapes, ornamental border"
# 负面词可用环境变量覆盖。★默认已加「两个月亮」相关词：
# 2026-10-28 实测 concept_only 组 8/8 都出现「小月 + 大圆月」，是过拟合的高频伪影，
# 提示词层面先压，不必为此重训。
NEG="${NEG:-photograph, realistic lighting, chiaroscuro, 3d render, anime, oil painting, western perspective, watermark, text, artist name, signature, two moons, double moon, repeated moons, multiple suns, ring moon, concentric circles in the sky, donut shape moon}"
# 输出偏青绿+金、缺朱砂，故把颜色写成带色相的短语并前置朱砂（2026-10-28 观察）
PAL="${PAL:-cinnabar red accents, azurite blue, malachite green, gold}"

[ -f "$CKPT" ] || { echo "未找到 SDXL base: $CKPT"; exit 1; }
[ -f "$CONCEPT_LORA" ] || { echo "未找到概念 LoRA: $CONCEPT_LORA"; exit 1; }

echo "== 风格 LoRA 校验（10-10 好版应为 6d4af5c7；9edebbfc 是 10-09 坏版）=="
if [ -f "$STYLE_LORA" ]; then
  H=$(sha256sum "$STYLE_LORA" | cut -c1-8)
  echo "  $H  $STYLE_LORA"
  # ★必须用 if 而不是 `[ ... ] && {...}`：条件为假时整个 && 列表返回 1，
  # 在 set -e 下会让脚本静默退出（2026-10-28 就是这么卡住的，日志停在哈希那一行）
  if [ "$H" = "9edebbfc" ]; then
    die "这是 10-09 坏版（出黑图），别用"
  fi
  if [ "$H" != "6d4af5c7" ]; then
    echo "  !! 哈希不在已知基准内，请确认来源"
  fi
else
  echo "  !! 缺风格 LoRA: $STYLE_LORA"
  [ "$MODE" = "concept_only" ] || exit 1
fi

case "$MODE" in
  concept_only) LORAS="$CONCEPT_LORA;$MUL_CONCEPT" ;;
  both)
    # ★这版 kohya 的 sdxl_minimal_inference.py 不支持逗号传多个 LoRA
    # （实测 ValueError: too many values to unpack，2026-10-28）。
    # 故先用 kohya 自带的 merge_lora.py 按权重比合成一个文件，再以 1.0 挂上。
    # ★不能写成 `MERGE=$(ls A B 2>/dev/null | head -1)`：B 不存在时 ls 返回 2，
    # 而 set -o pipefail 会让整条管道判失败、脚本静默退出（2026-10-28 卡在这，EXIT=2 无输出）
    MERGE=""
    for c in "$SD/networks/merge_lora.py" "$SD/scripts/networks/merge_lora.py"; do
      if [[ -f "$c" ]]; then MERGE="$c"; break; fi
    done
    [[ -n "$MERGE" ]] || die "找不到 kohya 的 merge_lora.py，无法叠加两个 LoRA（可先用 MODE=concept_only）"
    MERGED="$PRJ/output/lora/_merged_${SLUG}_s${MUL_STYLE}_c${MUL_CONCEPT}.safetensors"
    echo "== 合并 LoRA（风格 $MUL_STYLE + 概念 $MUL_CONCEPT）=="
    ( cd "$SD" && PYTHONPATH="$SD" python "$MERGE" \
        --save_precision fp16 --save_to "$MERGED" \
        --models "$STYLE_LORA" "$CONCEPT_LORA" \
        --ratios "$MUL_STYLE" "$MUL_CONCEPT" --concat )
    [[ -s "$MERGED" ]] || die "合并失败：$MERGED"
    LORAS="$MERGED;1.0" ;;
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
