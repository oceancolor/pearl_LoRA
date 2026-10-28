#!/usr/bin/env bash
# gpu_concept_run.sh — 新 GPU 机一条命令：装环境 -> 取底模 -> 备 tokenizer -> 训练概念 LoRA -> 归档
#
# 用法（在 GPU 机上）：
#   cd ~/pearl_LoRA && git checkout -- configs/ && git pull
#   nohup bash scripts/gpu_concept_run.sh > ~/concept_run.log 2>&1 &
#   tail -f ~/concept_run.log
#
#   只训某几支：nohup bash scripts/gpu_concept_run.sh ritual > ~/concept_run.log 2>&1 &
#
# 每段都幂等：中途断了直接重跑，已完成的会跳过。
# 本机实测约束（CODEBUDDY.md）：Python 须 >=3.10；torch 须 cu121（requirements 会带进 cu130，驱动跑不了）；
# 不装 xformers（走 sdpa）；fp16 + no_half_vae（已写在 configs/sdxl_lora_concept.toml）。
set -euo pipefail

SLUGS=("$@")
(( ${#SLUGS[@]} )) || SLUGS=(ritual water future_seed)

S="${SHARED:-/taijifs_hzlf31/share1227201/pearl_LoRA}"
PRJ="${PROJECT_DIR:-$HOME/pearl_LoRA}"
SD="${SD_SCRIPTS:-$HOME/sd-scripts}"
VENV="$HOME/venv"
TOK="$S/cache/tokenizers"
STAMP="$(date +%Y%m%d_%H%M)"

step() { echo; echo "==== $* ===="; date '+%F %T'; }
die()  { echo "!! $*"; exit 1; }

# ---------------------------------------------------------------- 0. 共享缓存
step "[0/7] 共享缓存（换机器后 pip / tokenizer 不用重下）"
[[ -d "$S" ]] || die "共享存储不可见：$S"
mkdir -p "$S/cache/pip" "$S/cache/hf" "$TOK" "$S/workspace"
cat > "$S/env.sh" <<EOF
export S=$S
export PIP_CACHE_DIR=$S/cache/pip
export HF_HOME=$S/cache/hf
[ -f $VENV/bin/activate ] && source $VENV/bin/activate
EOF
export PIP_CACHE_DIR="$S/cache/pip" HF_HOME="$S/cache/hf"
echo "以后登录先：source $S/env.sh"

# ---------------------------------------------------------------- 1. Python 3.11 + venv
step "[1/7] Python 3.11 + venv"
if ! command -v python3.11 >/dev/null; then
  dnf install -y python3.11 python3.11-pip || die "dnf 装 python3.11 失败"
fi
[[ -f "$VENV/bin/activate" ]] || python3.11 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -V
python -m pip install -q --upgrade pip

# ---------------------------------------------------------------- 2. kohya + 依赖 + cu121 torch
step "[2/7] kohya sd-scripts + 依赖"
if [[ "${SKIP_INIT:-0}" == "1" ]]; then
  echo "SKIP_INIT=1：跳过克隆与依赖安装（环境已就绪时用）"
else
  [[ -d "$SD/.git" ]] || git clone https://github.com/kohya-ss/sd-scripts.git "$SD"
  if [[ ! -f "$SD/.deps_ok" ]]; then
    ( cd "$SD" && pip install -r requirements.txt && pip install bitsandbytes )
    touch "$SD/.deps_ok"
  fi
fi
if ! python -c "import torch,sys; sys.exit(0 if torch.version.cuda=='12.1' and torch.cuda.is_available() else 1)" 2>/dev/null; then
  echo "torch 不是 cu121 或 CUDA 不可用 -> 重装 cu121"
  pip install --force-reinstall --index-url https://download.pytorch.org/whl/cu121 torch torchvision
fi
pip uninstall -y xformers >/dev/null 2>&1 || true
python -c "import torch;print('torch',torch.__version__,'cuda',torch.version.cuda,'available',torch.cuda.is_available(),torch.cuda.get_device_name(0))"
python -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" || die "CUDA 不可用"

# ---------------------------------------------------------------- 3. 代码与数据
step "[3/7] 仓库与概念集"
cd "$PRJ"
git checkout -- configs/ 2>/dev/null || true
git pull --ff-only || echo "WARN: git pull 失败，用现有版本继续"
git --no-pager log --oneline -1
python scripts/concept_check.py | tail -4

# ---------------------------------------------------------------- 4. 底模
step "[4/7] SDXL 底模"
mkdir -p "$PRJ/models"
M="$PRJ/models/sd_xl_base_1.0.safetensors"
if [[ ! -s "$M" ]]; then
  # 归档目录优先：workspace/*/models/ 下是上次备份的完整底模
  SRC=$(find "$S" -maxdepth 6 -path "*workspace*" -name sd_xl_base_1.0.safetensors -size +6G 2>/dev/null | sort | tail -1)
  [[ -n "$SRC" ]] || SRC=$(find "$S" -maxdepth 6 -name sd_xl_base_1.0.safetensors -size +6G 2>/dev/null | sort | tail -1)
  [[ -n "$SRC" ]] || die "共享存储里找不到 sd_xl_base_1.0.safetensors"
  echo "链接 $SRC"
  ln -sf "$SRC" "$M"
fi
ls -lhL "$M"

# 风格 LoRA 认准 f62a（10-10 版）；同名的 b038 是坏版（fp16 VAE 溢出），别拷
for f in $(find "$S" -maxdepth 6 -name "decomineral_v1_16gb*.safetensors" 2>/dev/null); do
  h=$(sha256sum "$f" | cut -c1-8)
  echo "  发现风格 LoRA: $f  哈希前缀 $h"
  [[ "$h" == f62a* ]] && cp -u "$f" "$PRJ/output/lora/" && echo "  -> 已采用 f62a 版"
done

# ---------------------------------------------------------------- 5. tokenizer（HF 被封时的退路）
step "[5/7] CLIP tokenizer"
T1="$TOK/openai_clip-vit-large-patch14"
T2="$TOK/laion_CLIP-ViT-bigG-14-laion2B-39B-b160k"
if [[ -d "$T1" && -d "$T2" ]]; then
  echo "已缓存于 $TOK"
elif curl -sfI -m 10 https://huggingface.co/openai/clip-vit-large-patch14/resolve/main/tokenizer_config.json >/dev/null; then
  echo "huggingface.co 可达，kohya 首次运行会下载并存到 $TOK"
elif curl -sfI -m 10 https://hf-mirror.com/openai/clip-vit-large-patch14/resolve/main/tokenizer_config.json >/dev/null; then
  echo "huggingface.co 不可达，改用镜像 hf-mirror.com"
  export HF_ENDPOINT=https://hf-mirror.com
  echo "export HF_ENDPOINT=https://hf-mirror.com" >> "$S/env.sh"
else
  # 最后退路：SDXL diffusers 仓库自带 tokenizer/ 与 tokenizer_2/（kohya 会把 pad_token_id 统一设为 0）
  D1=$(find "$S" -maxdepth 8 -type d -path "*stable-diffusion-xl-base-1.0*" -name tokenizer   2>/dev/null | head -1)
  D2=$(find "$S" -maxdepth 8 -type d -path "*stable-diffusion-xl-base-1.0*" -name tokenizer_2 2>/dev/null | head -1)
  if [[ -n "$D1" && -n "$D2" ]]; then
    echo "HF 与镜像都不可达，用 SDXL 自带 tokenizer：$D1 / $D2"
    cp -r "$D1" "$T1"; cp -r "$D2" "$T2"
  else
    die "tokenizer 无从获取：HF、hf-mirror 都不通，共享存储里也没有 SDXL diffusers 的 tokenizer 目录"
  fi
fi

# ---------------------------------------------------------------- 6. 训练
step "[6/7] 训练：${SLUGS[*]}"
DEST="$S/workspace/concept_$STAMP"
mkdir -p "$DEST"
export SD_SCRIPTS="$SD" MODEL="$M"
export EXTRA_ARGS="--tokenizer_cache_dir $TOK"
for slug in "${SLUGS[@]}"; do
  case "$slug" in
    ritual) trig=deco_ritual ;; water) trig=deco_water ;; future_seed) trig=deco_future ;;
    *) die "未知概念 $slug" ;;
  esac
  if [[ -f "$PRJ/output/lora/$trig.safetensors" ]]; then
    echo "-- $slug 已有成品 $trig.safetensors，跳过（要重训先删掉它）"
    continue
  fi
  echo "-- 开训 $slug（$trig）"
  ( cd "$PRJ" && bash scripts/train_concept.sh "$slug" ) || die "$slug 训练失败，看 $PRJ/logs/train_$slug.log"

  # 每训完一支立刻归档，机器随时释放也不丢
  mkdir -p "$DEST/lora" "$DEST/logs"
  cp -u "$PRJ"/output/lora/"$trig"*.safetensors "$DEST/lora/" 2>/dev/null || true
  [[ -d "$PRJ/output/lora/sample" ]] && cp -ru "$PRJ/output/lora/sample" "$DEST/lora/"
  cp -u "$PRJ/logs/train_$slug.log" "$DEST/logs/" 2>/dev/null || true
  echo "-- $slug 完成，已归档到 $DEST"
done

# ---------------------------------------------------------------- 7. 汇总
step "[7/7] 完成"
ls -lh "$DEST/lora"/*.safetensors 2>/dev/null || true
ls "$DEST/lora/sample" 2>/dev/null | tail -6 || true
echo "归档目录：$DEST"
