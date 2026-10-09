#!/usr/bin/env bash
# persist_artifacts.sh — 把「无法从 GitHub 重建」的产物归档到共享存储。
#
# 仓库里已有：脚本 / 配置 / prompts / provenance / 38 张训练图 + val（都在 git 里）。
# 本脚本只搬 git 里没有、且重新获取成本高或不可再得的东西：
#   1) SDXL base 权重（公司 IP 被 HF 封，重下很麻烦）
#   2) 训练产物：LoRA 权重 + 每 250 步抽检图（本次实验的唯一成果）
#   3) 训练日志
#   4) 环境快照：pip freeze / torch 版本 / kohya commit / 本次实际用的 configs
#
# 幂等：重复运行只增量拷贝（-u）。训练中也能跑，跑完再跑一次补齐最终产物。
#
# 用法：
#   bash scripts/persist_artifacts.sh /mnt/shared/pearl_LoRA
set -euo pipefail

DEST="${1:-}"
if [ -z "$DEST" ]; then
  echo "用法: bash scripts/persist_artifacts.sh <目标目录>"
  exit 1
fi
PRJ="${PROJECT_DIR:-$HOME/pearl_LoRA}"
STAMP="$(date +%Y%m%d_%H%M)"
OUT="$DEST/$STAMP"
mkdir -p "$OUT"

echo "== 归档到 $OUT =="

# 1) SDXL base 权重
if [ -f "$PRJ/models/sd_xl_base_1.0.safetensors" ]; then
  mkdir -p "$OUT/models"
  cp -u "$PRJ/models/sd_xl_base_1.0.safetensors" "$OUT/models/"
  echo "  [OK] SDXL base 权重"
else
  echo "  [--] 未找到 SDXL base 权重，跳过"
fi

# 2) 训练产物（LoRA + 抽检图）
if [ -d "$PRJ/output" ]; then
  mkdir -p "$OUT/output"
  cp -ur "$PRJ/output/." "$OUT/output/"
  echo "  [OK] output/（LoRA + 抽检图）"
fi

# 3) 训练日志
for f in /root/train_16gb.log /root/smoke_fp16.log "$PRJ/logs"/*; do
  [ -f "$f" ] || continue
  mkdir -p "$OUT/logs"
  cp -u "$f" "$OUT/logs/" 2>/dev/null || true
done
echo "  [OK] 日志"

# 4) 环境快照
mkdir -p "$OUT/env"
{ echo "date: $(date -Iseconds)"
  echo "python: $(python -V 2>&1)"
  python - <<'PY'
try:
    import torch
    print("torch:", torch.__version__, "| cuda:", torch.version.cuda)
except Exception as e:
    print("torch: N/A", e)
PY
  echo "kohya commit: $(git -C "${SD_SCRIPTS:-$HOME/sd-scripts}" rev-parse HEAD 2>/dev/null || echo N/A)"
  echo "gpu:"
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null || echo "  N/A"
} > "$OUT/env/env_info.txt"
pip freeze > "$OUT/env/pip_freeze.txt" 2>/dev/null || true
mkdir -p "$OUT/env/configs_used"
cp -u "$PRJ"/configs/*.toml "$OUT/env/configs_used/" 2>/dev/null || true
echo "  [OK] 环境快照"

echo "----------------------------"
echo "归档完成："
du -sh "$OUT" 2>/dev/null
find "$OUT" -maxdepth 2 -name "*.safetensors" -exec ls -lh {} \; 2>/dev/null | head
echo "提示：把这个目录拷到你自己的机器 / 对象存储，环境释放后也能继续。"
