#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""init_tree.py — decomineral 仓库骨架生成器。

依据 SPEC.md §4（目录）、§6.1（caption schema）、§7（生成期提示词合同）、
§8（硬件剖面）、§10 第 1 步（完成定义：目录可建、schema 可校验）。

设计原则：
  * 幂等：只创建缺失目录与骨架文件；已存在的生成物默认**不覆盖**（保护人工编辑），
    除非传 --force。
  * 自证：写盘后读回 schema 确认合法 JSON，并用 jsonschema（若可用）校验内置示例。
  * 不做训练、不下载、不引入攻击/盗权重逻辑（SPEC §0.1 / §0.9）。

用法：
    python scripts/init_tree.py            # 建骨架（不覆盖已有生成物）
    python scripts/init_tree.py --force    # 强制重写骨架生成物
    python scripts/init_tree.py --root D:/some/path
"""

import argparse
import json
import sys
from pathlib import Path

# Windows 控制台默认 GBK，print 非 GBK 字符会崩；强制 UTF-8（便携）。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = "8gb"  # 用户 GPU 显存 8GB（本次指令）；训练/生成只引用该剖面，勿混用。

# --------------------------------------------------------------------------- #
# 目录骨架（SPEC §4）
# --------------------------------------------------------------------------- #
DIRS = [
    "schema",
    "hardware",
    "prompts",
    "data",
    "data/inbox/raw",
    "data/inbox/review",
    "data/rejected",
    "data/crops",
    "data/train/images",
    "data/train/captions",
    "data/concept_lora",
    "data/concept_lora/ritual",
    "data/concept_lora/water",
    "data/concept_lora/future_seed",
    "scripts",
    "models",
    "output/lora",
    "logs",
]

# 需要保留在版本库里的空目录占位（SPEC §4）
GITKEEP = [
    "data/inbox/raw",
    "data/inbox/review",
    "data/rejected",
    "data/crops",
    "data/train/images",
    "data/train/captions",
    "data/concept_lora/ritual",
    "data/concept_lora/water",
    "data/concept_lora/future_seed",
    "models",
    "output/lora",
    "logs",
]

# --------------------------------------------------------------------------- #
# caption JSON Schema（SPEC §6.1，逐字段忠实转录）
# --------------------------------------------------------------------------- #
CAPTION_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "decomineral caption",
    "type": "object",
    "required": ["id", "style", "theme", "content", "caption_en", "license"],
    "properties": {
        "id": {"type": "string"},
        "license": {"enum": ["PD", "CC0"]},
        "family": {
            "enum": [
                "silkroad_mural",
                "persian_miniature",
                "bilibin",
                "clarkestain",
                "rimpa",
                "pure_ornament",
                "other_pd",
            ]
        },
        "style": {
            "type": "object",
            "required": ["traits"],
            "properties": {
                "traits": {
                    "type": "array",
                    "minItems": 4,
                    "items": {
                        "enum": [
                            "flat_fill",
                            "mineral_pigment",
                            "pattern_equals_form",
                            "no_chiaroscuro",
                            "closed_outline",
                            "ornamental_border",
                            "tapestry_space",
                            "gold_ground",
                            "enamel_cells",
                            "jewel_palette",
                            "patterned_terrain",
                            "radial_gradient",
                            "nonfocal_figures",
                        ]
                    },
                },
                "palette": {
                    "type": "array",
                    "items": {
                        "enum": [
                            "azurite",
                            "malachite",
                            "cinnabar",
                            "ochre",
                            "gold",
                            "jade_white",
                            "lapis",
                            "soot",
                            "coral",
                            "turquoise",
                        ]
                    },
                },
            },
        },
        "theme": {
            "type": "object",
            "required": ["primary"],
            "properties": {
                "primary": {
                    "enum": [
                        "ritual",
                        "court",
                        "nature",
                        "water",
                        "ornament",
                        "machine_or_sky",
                    ]
                },
                "secondary": {"type": "array", "items": {"type": "string"}},
            },
        },
        "content": {
            "type": "array",
            "items": {"type": "string"},
            "description": "nouns only: boat, wave-pattern, palace, bird, tree, throne. No artist names. No 'dunhuang style'.",
        },
        "composition": {
            "enum": [
                "full_page",
                "border_frame",
                "horizontal_register",
                "central_figure",
                "pattern_field",
                "crop_detail",
            ]
        },
        "caption_en": {"type": "string", "minLength": 40, "maxLength": 600},
        "notes_zh": {"type": "string"},
        "split": {"enum": ["train", "val"]},
    },
}

# schema 自检样本：合法 caption（caption_en 40–600、traits>=4、license CC0、无画家名）
EXAMPLE_VALID = {
    "id": "00001",
    "license": "CC0",
    "family": "persian_miniature",
    "style": {
        "traits": ["flat_fill", "mineral_pigment", "pattern_equals_form", "tapestry_space"],
        "palette": ["azurite", "malachite", "gold"],
    },
    "theme": {"primary": "water", "secondary": ["boat"]},
    "content": ["boat", "wave-pattern", "palace", "fish"],
    "composition": "full_page",
    "caption_en": (
        "decomineral style, flat mineral pigments, no chiaroscuro, pattern equal to form, "
        "tapestry space, a palace beside patterned water with two boats and fish-scale waves, "
        "malachite green, azurite blue, gold"
    ),
    "notes_zh": "示例：纹样化水波与宫殿，矿物色平涂。仅供 schema 自检，非训练数据。",
    "split": "train",
}

# schema 自检样本：非法 caption（license 越界 + traits 不足），应被拒
EXAMPLE_INVALID = {
    "id": "bad",
    "license": "CC-BY",
    "style": {"traits": ["flat_fill"]},
    "theme": {"primary": "water"},
    "content": ["boat"],
    "caption_en": "decomineral style, boat",
}

# --------------------------------------------------------------------------- #
# 骨架生成物（文本内容，忠实转录 SPEC）
# --------------------------------------------------------------------------- #
PROVENANCE_HEADER = (
    "file_id,orig_filename,train_filename,source,institution,page_url,direct_url,"
    "license,license_url,creator,creator_death_year,publication_year,family,theme_primary,"
    "width,height,sha256,decision,decision_reason,downloaded_at\n"
)

HW16_YAML = """\
# decomineral 硬件剖面（SPEC §8.1）。来源 SPEC，勿手改数值除非同步 SPEC。
# ★只引用 16gb.yaml 或 8gb.yaml 之一，勿混用（SPEC §0.8）。当前用户环境为 8GB。
profile: 16gb
preferred_base: flux1-dev          # 用户自备，遵守 FLUX 非商用条款
fallback_base: sdxl
lora:
  rank: 16
  alpha: 16
  blocks: default_for_flux_or_sdxl
train:
  resolution_buckets: [768, 896, 1024]
  batch_size: 1
  grad_accum: 4
  optimizer: adamw8bit
  lr: 1.0e-4
  lr_scheduler: cosine
  warmup_steps: 50
  max_train_steps: 2000            # 约 45–60 张时；按 30 张可 1500，70 张可 2500
  mixed_precision: bf16            # 不支持则 fp16
  gradient_checkpointing: true
  cache_latents: true
repeats_formula: "target_steps / (image_count * epochs) ; epochs=1–2"
time_budget_hours: 1.5
oom_fallback:
  - rank: 8
  - resolution_max: 896
  - cache_latents: false
notes:
  - 不要 full finetune
  - 不要把 text encoder 学太狠；FLUX 只训 LoRA
  - 每 250 step 出 4 张固定 prompt 抽检：ritual / court / water / future
"""

HW8_YAML = """\
# decomineral 硬件剖面（SPEC §8.2）—— 本次用户环境 8GB，训练/生成默认用此文件。
# ★只引用 16gb.yaml 或 8gb.yaml 之一，勿混用（SPEC §0.8）。
profile: 8gb
preferred_base: sdxl
disallow_default: flux1-dev        # 除非用户明确要 block-swap 且接受 3h+/轮
lora:
  rank: 8
  alpha: 8
train:
  resolution_buckets: [640, 768, 832]
  batch_size: 1
  grad_accum: 8
  optimizer: adamw8bit
  lr: 8.0e-5
  max_train_steps: 1800
  mixed_precision: fp16
  gradient_checkpointing: true
  cache_latents: true
  vae_slicing: true
time_budget_hours: 3
oom_fallback:
  - resolution_max: 704
  - rank: 4
  - 改 SD 1.5 仅作最后手段，需另写 caption 更短
notes:
  - 8GB 不要并行下载+训练
  - 训练图短边 768 即可，不要迷信 1024
"""

PROMPTS_YAML = """\
# decomineral 生成期提示词合同（SPEC §7）。风格锁永远同一句，主题只改 SUBJECT。
# 拼法：<lora:decomineral:0.8>, {style_lock}, {subject}, malachite, azurite, cinnabar, gold
style_lock: >-
  decomineral style, flat mineral pigments, no chiaroscuro,
  pattern equal to form, tapestry space, jewel-like palette,
  closed color shapes, ornamental border

negative: >-
  photograph, realistic lighting, chiaroscuro, 3d render, anime,
  oil painting, western perspective, watermark, text, artist name

branches:
  ritual:
    subject: >-
      a ceremonial hall with canopy, attendants, sacred tree and
      geometric pavement, ritual but not a copy of a known cave
  future:
    subject: >-
      an orbital palace and procession of machine-bodied attendants,
      towers like sutra pillars, sky-boats treated as ornament not sci-fi chrome
  water:
    subject: >-
      an underwater palace, fish-scale waves, lotus as fabric, boats
      and palaces stacked like a tapestry
  # TODO(SPEC §8/§9)：抽检需 ritual/court/water/future 四条，SPEC §7 未给 court branch subject，
  # 待补 court 分支后再写 prompts/eval_grid.txt（同一随机种子两台机对照）。勿臆造、勿爬在世作者。
"""

DATA_README = """\
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
"""

GEN_FILES = {
    "schema/caption.schema.json": None,  # None => 由 CAPTION_SCHEMA 序列化
    "hardware/16gb.yaml": HW16_YAML,
    "hardware/8gb.yaml": HW8_YAML,
    "prompts/generate_en.yaml": PROMPTS_YAML,
    "data/provenance.csv": PROVENANCE_HEADER,
    "data/README.md": DATA_README,
}


def render(rel: str, text):
    if rel.endswith("caption.schema.json"):
        return json.dumps(CAPTION_SCHEMA, ensure_ascii=False, indent=2) + "\n"
    return text


def verify_schema(schema: dict):
    """返回 (status, message)，status ∈ ok|skip|fail。"""
    try:
        from jsonschema import Draft202012Validator
    except Exception as exc:  # noqa: BLE001
        return "skip", (
            "jsonschema 未安装（%s）；schema 已确认为合法 JSON，但示例校验跳过。"
            "如需自证请 `pip install jsonschema` 后复跑。" % exc
        )
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:  # noqa: BLE001
        return "fail", "schema 自身非法：%s" % exc
    validator = Draft202012Validator(schema)
    errs_valid = list(validator.iter_errors(EXAMPLE_VALID))
    errs_invalid = list(validator.iter_errors(EXAMPLE_INVALID))
    if errs_valid:
        return "fail", "合法示例未通过：" + "; ".join(e.message for e in errs_valid)
    if not errs_invalid:
        return "fail", "非法示例竟通过校验，schema 约束过松。"
    return "ok", "schema 校验通过（合法示例通过 / 非法示例被正确拒 %d 条）。" % len(errs_invalid)


def main(argv=None):
    ap = argparse.ArgumentParser(description="decomineral 骨架生成器（SPEC §10 第 1 步）")
    ap.add_argument("--force", action="store_true", help="重写已存在的骨架生成物")
    ap.add_argument("--root", default=str(ROOT), help="仓库根（默认脚本上级目录）")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    made_dirs, made_keep, wrote, skipped = [], [], [], []

    for rel in DIRS:
        p = root / rel
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            made_dirs.append(rel)

    for rel in GITKEEP:
        gp = root / rel / ".gitkeep"
        if not gp.exists():
            gp.write_text("", encoding="utf-8")
            made_keep.append(rel + "/.gitkeep")

    for rel, text in GEN_FILES.items():
        p = root / rel
        existed = p.exists()
        if existed and not args.force:
            skipped.append(rel)
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render(rel, text), encoding="utf-8")
        wrote.append(("重写 " if existed else "新建 ") + rel)

    # 读回自证：schema 必须是合法 JSON
    try:
        schema_on_disk = json.loads((root / "schema/caption.schema.json").read_text("utf-8"))
    except Exception as exc:  # noqa: BLE001
        schema_on_disk = CAPTION_SCHEMA
        print("警告：读回 schema 失败（%s），改用内存对象校验。" % exc)
    status, msg = verify_schema(schema_on_disk)

    print("== decomineral init_tree ==")
    print("仓库根：%s" % root)
    print("默认硬件剖面：%s（用户显存 8GB；训练/生成勿混用另一剖面）" % DEFAULT_PROFILE)
    print("目录：新建 %d 个" % len(made_dirs))
    print("占位：新建 .gitkeep %d 个" % len(made_keep))
    print("生成物：\n  - " + ("\n  - ".join(wrote) if wrote else "（无）"))
    if skipped:
        print("已存在跳过（加 --force 可重写）：\n  - " + "\n  - ".join(skipped))
    print("schema 校验：[%s] %s" % (status, msg))
    print("\n下一步（SPEC §10）：第 2 步实现 scripts/license_gate.py。"
          " 待补：prompts/eval_grid.txt（court branch 缺失，见 §7/§8 缺口）。")
    if status == "fail":
        sys.exit(1)


if __name__ == "__main__":
    main()
