#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""caption_lint.py — caption 与配额门禁（SPEC §6.3；§3.3 theme 配额）。

检查每条 data/train/images/NNNNN.txt 与同名 .json：
  1) .txt 以小写 'decomineral style' 开头
  2) 不含黑名单词（画家名/敦煌/动画/垃圾词等）
  3) 至少 1 个 form-grammar 短语
  4) 至少 1 个 content 名词
  5) .json 通过 schema/caption.schema.json（装了 jsonschema 时）
  6) theme.primary 与 caption 大意不冲突（如 water 须含 water/wave/boat/fish/lotus 之一）
  7) 统计 theme 分布，正式不满足 §3.3 配额则 FAIL；冒烟可 --smoke 降级为 WARN
退出码非 0 表示有 FAIL。

用法：
    python scripts/caption_lint.py --train data/train/images
    python scripts/caption_lint.py --train data/train/images --smoke
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]

PREFIX = "decomineral style"

BLACKLIST = [
    "dunhuang style", "mogao style", "bilibin style", "nielsen", "ngai", "ye luying",
    "earle", "le cain", "nine-color", "nine color", "jiu se lu", "ming zhu",
    "in the style of", "chinese animation", "anime", "photoreal", "8k", "masterpiece",
    "cai chuanlong",
]

FORM_GRAMMAR = [
    "flat mineral pigments", "no chiaroscuro", "pattern equal to form", "closed color shapes",
    "ornamental border", "tapestry space", "gold ground", "enamel cell outlines",
    "jewel-like palette", "woven feathers", "patterned water", "patterned clouds",
    "geometric pavement",
    # v1.1 装饰画传统技法（SPEC §13）
    "mountains patterned as dense forest", "color radiating outward from the center",
    "figures in large non-focal areas",
]

THEME_HINTS = {
    "ritual": ["ritual", "canopy", "attendant", "sacred", "throne", "offering", "procession", "figure", "seated"],
    "court": ["palace", "court", "throne", "textile", "city", "wall", "pavilion", "hall"],
    "nature": ["tree", "bird", "flower", "mountain", "rock", "crane", "leaf", "cloud"],
    "water": ["water", "wave", "boat", "fish", "lotus", "river", "pond", "sea"],
    "ornament": ["ornament", "pattern", "border", "motif", "geometric", "design", "carpet"],
    "machine_or_sky": ["machine", "sky", "star", "chariot", "rocket", "orbital", "tower", "wheel", "cloud"],
}

# §3.3 主题最少张数（train split）
THEME_MIN = {"ritual": 8, "court": 8, "nature": 8, "water": 8, "ornament": 6, "machine_or_sky": 4}

# 软配额：SPEC §3.3 明写「尽量找，PD 里少，缺则保持 4，禁止用现代科幻插画补」，
# 即该主题允许为 0；缺它只 WARN，不 FAIL。其余主题是硬配额。
THEME_SOFT = {"machine_or_sky"}

CONTENT_FORBID = ["dunhuang", "mogao", "bilibin", "style", "painting of"]


def load_validator():
    """返回 (validator_or_None, note)。validator=None 表示跳过结构校验。"""
    sp = ROOT / "schema/caption.schema.json"
    try:
        schema = json.loads(sp.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, "无法读取 schema：%s（先跑 init_tree.py）" % exc
    try:
        from jsonschema import Draft202012Validator
    except Exception:
        return None, "jsonschema 未安装，跳过 .json 结构校验（pip install jsonschema 复跑）。"
    return Draft202012Validator(schema), "schema 结构校验已启用。"


def lint_one(txt_path, json_path, validator, problems):
    cap = txt_path.read_text(encoding="utf-8").strip()
    low = cap.lower()
    tag = txt_path.name

    if not low.startswith(PREFIX):
        problems.append((tag, "开头须为 '%s'（小写）" % PREFIX))

    for b in BLACKLIST:
        if b in low:
            problems.append((tag, "命中黑名单词 '%s'" % b))

    if not any(fg in low for fg in FORM_GRAMMAR):
        problems.append((tag, "缺 form-grammar 短语（§6.2）"))

    data = None
    jpath = txt_path.with_suffix(".json")
    if jpath.exists():
        try:
            data = json.loads(jpath.read_text(encoding="utf-8"))
        except Exception as exc:
            problems.append((tag, ".json 解析失败：%s" % exc))
    else:
        problems.append((tag, "缺同名 .json（三件套，§6）"))

    if isinstance(data, dict):
        content = [str(c).lower() for c in (data.get("content") or [])]
        if not content:
            problems.append((tag, ".json content 为空（缺名词，§6.1）"))
        for c in content:
            for bad in CONTENT_FORBID:
                if bad in c:
                    problems.append((tag, "content 含越界词 '%s'（应普通名词，§6.1）" % c))
        if validator is not None:
            for e in validator.iter_errors(data):
                problems.append((tag, "schema 不符：%s" % e.message))
        theme = (data.get("theme") or {}).get("primary")
        hints = THEME_HINTS.get(theme)
        if theme and hints and not any(h in low for h in hints):
            problems.append((tag, "theme=%s 但 caption 未出现对应意象（§6.3 第5条）" % theme))
    return data


def main():
    ap = argparse.ArgumentParser(description="decomineral caption lint")
    ap.add_argument("--train", default=str(ROOT / "data/train/images"))
    ap.add_argument("--smoke", action="store_true", help="冒烟模式：配额未达仅 WARN，不 FAIL")
    args = ap.parse_args()

    train_dir = Path(args.train)
    if not train_dir.exists():
        print("目录不存在：%s" % train_dir)
        sys.exit(1)

    validator, note = load_validator()
    print("caption_lint：%s" % note)

    txts = sorted(train_dir.glob("*.txt"))
    if not txts:
        print("train 下没有 .txt（还没有可训图，见 §5/§6）。")
        sys.exit(2)

    problems = []
    theme_train = Counter()
    n_val = 0
    for txt in txts:
        data = lint_one(txt, txt.with_suffix(".json"), validator, problems)
        if isinstance(data, dict):
            if data.get("split", "train") == "val":
                n_val += 1
            else:
                th = (data.get("theme") or {}).get("primary")
                if th:
                    theme_train[th] += 1

    print("== 扫描 %d 条 caption（train=%d, val=%d）==" % (len(txts), sum(theme_train.values()), n_val))

    hard_fail = bool(problems)
    if problems:
        print("发现问题 %d 条：" % len(problems))
        for tag, msg in problems:
            print("  - [%s] %s" % (tag, msg))
    else:
        print("逐条 caption 规则：全部通过。")

    print("theme 分布(train)：%s" % dict(theme_train))
    deficit = {t: THEME_MIN[t] - theme_train.get(t, 0) for t in THEME_MIN if theme_train.get(t, 0) < THEME_MIN[t]}
    soft_deficit = {t: d for t, d in deficit.items() if t in THEME_SOFT}
    hard_deficit = {t: d for t, d in deficit.items() if t not in THEME_SOFT}
    quota_fail = bool(hard_deficit)
    if soft_deficit:
        print("[WARN] 软配额未达（§3.3 允许保留）：%s" % soft_deficit)
    if hard_deficit:
        line = "theme 配额未达 §3.3：%s" % hard_deficit
        if args.smoke:
            print("[WARN] %s（冒烟模式忽略；正式训练前必须补齐）" % line)
        else:
            print("[FAIL] %s" % line)

    print("-" * 60)
    if hard_fail or (quota_fail and not args.smoke):
        print("结果：FAIL（%d 问题%s）" % (len(problems), "" if not quota_fail else " + 配额未达"))
        sys.exit(1)
    if soft_deficit and not hard_deficit:
        print("结果：PASS（§3.3 硬配额全部达标；软配额保留）")
        sys.exit(0)
    print("结果：%s" % ("PASS(冒烟，未满足正式配额)" if (args.smoke and quota_fail) else "PASS"))
    sys.exit(0)


if __name__ == "__main__":
    main()
