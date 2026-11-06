#!/usr/bin/env bash
# 风格 LoRA v2 重训（提高泛化）——渲染配置并启动 kohya
#
# 前置条件：先 review 以下改动（见 sdxl_lora_v2.toml 头部说明）：
#   1. 触发词 decomineral -> mirlak（de/com/in 高频碎片 -> 无语义碎片）
#   2. captions_v2（去掉 pattern equal to form 等抽象短语，53->40 词）
#   3. reg_set 负例（base 生成的通用图，教模型"无触发词时保持先验"）
#   4. repeats 大幅下调：v1 每图 ~200 次曝光 -> v2 ~30 次
#
# 用法: bash /root/workspace/benjamin/next_train/train_style_v2.sh
set -euo pipefail
B=/root/workspace/benjamin
NT=$B/next_train
P=$B/pearl_LoRA/workspace
RUN=$B/train_runs/v2_$(date +%Y%m%d_%H%M)   # 训练成果统一落盘到共享盘本人目录
mkdir -p "$RUN/configs" "$RUN/output" "$RUN/logs"

PY=$B/venv/bin/python
# TMPDIR 不能用共享盘：dop-fuse 不支持 bash heredoc 的临时文件创建方式
export PIP_CACHE_DIR=$B/cache/pip HF_HOME=$B/cache/hf TMPDIR=/tmp
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
# venv 里的 opencv-python 需要 libGL.so.1；本机没有系统 libgl，用 CUDA 自带的 Mesa 库补齐
export LD_LIBRARY_PATH=/usr/local/cuda-12.1/nsight-systems-2023.1.2/host-linux-x64/Mesa:${LD_LIBRARY_PATH:-}

# 0) 负例集（已存在则跳过）
if [ "$(find "$NT/reg_set/images" -name '*.png' 2>/dev/null | wc -l)" -lt 20 ]; then
  echo "[v2] generating reg set..."
  "$PY" "$NT/make_reg_set.py" --n 24
fi

# 1) 新触发词版 caption
python3 "$NT/rebalance_captions.py" \
  --src "$P/data/train/images" \
  --out "$NT/captions_v2_mirlak" --trigger mirlak

# 2) 组装训练目录：图片 + v2 caption（软链，不动原始数据）
DATA=$RUN/data; mkdir -p "$DATA"
for img in "$P/data/train/images"/*.png "$P/data/train/images"/*.jpg; do
  [ -e "$img" ] || continue
  id=$(basename "$img"); id=${id%.*}
  ln -sf "$img" "$DATA/$id.${img##*.}"
  cp "$NT/captions_v2_mirlak/$id.txt" "$DATA/$id.txt"
done
N_IMG=$(find "$DATA" \( -name '*.png' -o -name '*.jpg' \) | wc -l)
N_REG=$(find "$NT/reg_set/images" -name '*.png' | wc -l)
echo "[v2] style imgs=$N_IMG reg imgs=$N_REG"

# 3) 渲染 dataset toml：每图总曝光目标 ~30 次
#    steps=1000, grad_accum=4 -> 4000 样本; (38+24)*30 ≈ 1860 -> repeats 取 15
sed -e "s|__TRAIN_DIR__|$DATA|g" \
    -e "s|__REG_DIR__|$NT/reg_set/images|g" \
    -e "s|__REPEATS__|15|g" \
    -e "s|__REG_REPEATS__|15|g" \
    "$NT/dataset_v2.toml" > "$RUN/configs/dataset_v2.toml"

# 4) 渲染 train toml
sed -e "s|__BASE_MODEL__|$B/models/sd_xl_base_1.0.safetensors|g" \
    -e "s|__DATASET_TOML__|$RUN/configs/dataset_v2.toml|g" \
    -e "s|__OUTPUT_DIR__|$RUN/output|g" \
    -e "s|__OUTPUT_NAME__|decomineral_v2|g" \
    -e "s|__LOG_DIR__|$RUN/logs|g" \
    -e "s|__STEPS__|1000|g" \
    -e "s|__SAMPLE_PROMPTS__|$NT/sample_prompts_v2.txt|g" \
    "$NT/sdxl_lora_v2.toml" > "$RUN/configs/sdxl_lora_v2.toml"

# 5) 训练中自采样（含 OOD 主体，测泛化）
printf '%s\n' \
  'mirlak style, a steam locomotive crossing a stone bridge --w 896 --h 896 --s 28 --d 20261106 --l 6' \
  'mirlak style, an elderly fisherman portrait, natural light --w 896 --h 896 --s 28 --d 20261107 --l 6' \
  'mirlak style, a bowl of ramen on a wooden table --w 896 --h 896 --s 28 --d 20261108 --l 6' \
  > "$NT/sample_prompts_v2.txt"

echo "[v2] starting training -> $RUN"
cd "$B/sd-scripts"
"$PY" sdxl_train_network.py \
  --config_file "$RUN/configs/sdxl_lora_v2.toml" \
  2>&1 | tee "$RUN/logs/train_v2.log"
echo "[v2] TRAIN_EXIT=${PIPESTATUS[0]}"
