#!/usr/bin/env python
"""caption 重构：减少触发词与"几何图案化"属性的绑定。

背景（对 38 张风格集 caption 的统计）：
  - 38/38 前 5 个 token 完全相同：decomineral style, flat mineral pigments,
    no chiaroscuro, ... → 触发词吸收全部视觉属性
  - "pattern equal to form" / "tapestry space" 等 35/38 高频抽象短语
    对 CLIP 是噪声锚点，强化"任何提示都往纹样走"
  - 平均 53.7 词过长

输出到新目录，不覆盖原 caption。与 dataset_v2.toml 配套（shuffle_caption=true）。

用法:
  python3 rebalance_captions.py \
      --src /root/workspace/benjamin/pearl_LoRA/workspace/data/train/images \
      --out /root/workspace/benjamin/next_train/captions_v2 \
      [--trigger mirlak]   # 可选：同时更换触发词（v1 风格词 decomineral 的切词含高频碎片 in/com）
"""
import argparse
import glob
import json
import os
import re

# 只在这些图（按 metadata trait 标注）保留的短语；其余从 caption 中移除
TRAIT_PHRASES = {
    "pattern_equals_form": "pattern equal to form",
    "tapestry_space": "tapestry space",
    "ornamental_border": "ornamental border",
    "closed_outline": "closed color shapes",
    "gold_ground": "gold ground",
}
# 固定前缀压缩后保留的核心风格段（可泛化材质特征）
CORE_PREFIX = "flat mineral pigments, no chiaroscuro"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--trigger", default=None, help="替换触发词（默认保留 decomineral）")
    ap.add_argument("--max-words", type=int, default=40)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    changed = kept = 0
    for txt in sorted(glob.glob(os.path.join(args.src, "*.txt"))):
        cap = open(txt).read().strip()
        base_id = os.path.splitext(os.path.basename(txt))[0]
        meta_p = os.path.join(args.src, base_id + ".json")
        traits = []
        if os.path.exists(meta_p):
            m = json.load(open(meta_p))
            traits = set(m.get("style", {}).get("traits", []))
            if m.get("caption_en"):
                cap = m["caption_en"]  # 以 metadata 为准（与训练时一致）

        # 1) 拆掉固定前缀中的抽象短语（未在 traits 标注的一律删；都标注的也删——由图像自身承载）
        for trait, phrase in TRAIT_PHRASES.items():
            cap = cap.replace(phrase + ", ", "").replace(", " + phrase, "")
        # 2) 触发词处理：decomineral style -> [trigger] style
        new_trig = (args.trigger + " style") if args.trigger else "decomineral style"
        cap = re.sub(r"^decomineral style", new_trig, cap)
        # 3) 重建前缀：触发词 + 核心材质段
        cap = re.sub(r"^(\S+\s+style,\s*)flat mineral pigments,\s*no chiaroscuro,\s*",
                     "", cap)
        cap = new_trig + ", " + CORE_PREFIX + ", " + cap
        # 4) 限长（保头截尾，颜色表在尾部可截）
        words = cap.split()
        if len(words) > args.max_words:
            cap = " ".join(words[: args.max_words]).rstrip(",") 
        # 清理连续逗号/空格
        cap = re.sub(r"\s+", " ", cap)
        cap = re.sub(r",\s*,", ",", cap).strip().rstrip(",")

        out_p = os.path.join(args.out, base_id + ".txt")
        with open(out_p, "w") as f:
            f.write(cap + "\n")
        changed += 1
    print(f"[captions_v2] wrote {changed} -> {args.out} (trigger={'changed' if args.trigger else 'decomineral (kept)'})")


if __name__ == "__main__":
    main()
