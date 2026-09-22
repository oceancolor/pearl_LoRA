#!/usr/bin/env bash
# init_gpu.sh — GPU 训练机初始化（decomineral LoRA / kohya sd-scripts）
# 用法：bash scripts/init_gpu.sh [sd-scripts 目录]   默认 ~/sd-scripts
# 幂等：重复运行安全。只做环境准备，不启动训练（SPEC §0.1）。
set -euo pipefail

SD="${1:-$HOME/sd-scripts}"
PY="${PYTHON:-python3}"

echo "==== [1/6] 机器信息 ===="
uname -a
$PY -V
nvidia-smi || echo "WARN: nvidia-smi 不可用"

echo "==== [2/6] torch / CUDA ===="
$PY -c "import torch;print('torch',torch.__version__,'cuda',torch.version.cuda,'available',torch.cuda.is_available(),torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')" || echo "WARN: torch 未安装或不可用"

echo "==== [3/6] kohya sd-scripts ===="
if [ -d "$SD/.git" ]; then
  echo "已存在，更新：$SD"
  git -C "$SD" pull --ff-only || true
else
  echo "克隆到 $SD"
  git clone https://github.com/kohya-ss/sd-scripts.git "$SD"
fi

echo "==== [4/6] Python 依赖 ===="
$PY -m pip install --upgrade pip
$PY -m pip install -r "$SD/requirements.txt"
# 8GB 剖面用 AdamW8bit；xformers 按 torch 版本二选一
$PY -m pip install bitsandbytes || echo "WARN: bitsandbytes 安装失败（AdamW8bit 不可用）"
$PY -m pip install xformers || echo "WARN: xformers 安装失败（可在 toml 里改 sdpa=true）"
$PY -m pip install tensorboard || true

echo "==== [5/6] 项目骨架与数据 ===="
PRJ="${PROJECT_DIR:-$HOME/pearl_LoRA}"
if [ -d "$PRJ/.git" ]; then
  git -C "$PRJ" pull --ff-only || true
else
  echo "请自行把 pearl_LoRA 仓库放到 $PRJ（rsync/scp/git clone）；"
  echo "本项目不是 git 仓库（CODEBUDDY.md），脚本不代你建。"
fi
ls -la "$PRJ/data/train/images" 2>/dev/null | head -5 || echo "WARN: 未见训练图"
ls -la "$PRJ/models" 2>/dev/null || echo "WARN: 未见 models/（SDXL base 需自备，SPEC §0.9）"

echo "-- 改写 configs 绝对路径（Windows -> 本机）--"
if [ -f "$PRJ/scripts/patch_configs.py" ]; then
  ( cd "$PRJ" && $PY scripts/patch_configs.py --project-dir "$PRJ" ) || echo "WARN: patch_configs 失败"
else
  echo "WARN: 未见 scripts/patch_configs.py，需手改 configs/*.toml"
fi
echo "核对："
grep -n "image_dir\|pretrained_model_name_or_path\|output_dir\|logging_dir" \
  "$PRJ/configs/dataset_8gb.toml" "$PRJ/configs/sdxl_lora_8gb.toml" 2>/dev/null || true

echo "==== [6/6] 体检 GO / NO-GO ===="
if [ -d "$PRJ" ]; then
  ( cd "$PRJ" && $PY scripts/env_check.py --sd-scripts "$SD" ) || true
fi
echo "提醒：已自动改写 configs 路径；若 models/ 下有多个 safetensors，"
echo "      用 --model 指定正确的那一个后重跑 patch_configs.py。"
