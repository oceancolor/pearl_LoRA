# data/ — 数据集与许可账本

骨架由 `scripts/init_tree.py` 生成。数据流、配额与标注格式以 SPEC.md §3–§6 为准。
当前硬件剖面：**8gb**（用户 GPU 显存 8GB）；训练/生成只引用 `hardware/8gb.yaml`，勿与 16gb 混用。

目录职责（SPEC §4 / §5）：
- `provenance.csv`：许可账本。**没有 provenance 记录的图像等于不存在**（SPEC §0.3）。
  `decision` 列取值 ∈ `train | review | reject`。
- `inbox/raw/`：原样下载（原图 + 许可片段 + sha256），**永不直接训练**（§5.1）。已 gitignore。
- `inbox/review/`：CC-BY / CC-BY-SA / 「no known restrictions 但非 CC0」复核队列，人工定夺（§2.2）。
- `rejected/`：被拒图像 + 拒绝理由（§2.3）。
- `crops/`：人工 / 半自动裁切产物（§5.3）。
- `train/images/`：最终训练三件套 `NNNNN.{png,jpg}` + 同名 `.txt` + 同名 `.json`（§6）。8gb 短边≥768。
- `train/captions/`：可选，caption 不放 images 旁时使用。
- `concept_lora/{ritual,water,future_seed}/`：风格 LoRA 稳定后的概念 LoRA 数据（§7），每支 15–25 张，触发词另起。

配额（训练前必须满足）：
- 风格家族 A–G（§3.2），目标入库 45–70 张；同一面墙/同一页书最多 3 张裁切。
- 主题 `theme.primary`：ritual/court/nature/water 各 ≥8、ornament ≥6、machine_or_sky ≥4（§3.3）；
  `future` 不是训练集主题，machine_or_sky 缺则保持 4，禁止用现代科幻补。

校验：`python scripts/caption_lint.py --train data/train/images`（§6.3；脚本待 SPEC §10 第 5 步实现）。
