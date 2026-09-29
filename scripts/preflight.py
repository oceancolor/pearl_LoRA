#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""preflight.py — 训练前自检（一条命令出 GO / NO-GO）。

把「开训前要人肉确认一遍」的东西机器化：三道门 + 三件套完整性 + 册/图双向链接
+ val 未混入 train + 短边门槛 + metadata 条数。不下载、不训练、不改任何文件。

用法：
    python scripts/preflight.py                 # 默认 8gb 剖面
    python scripts/preflight.py --profile 16gb
    python scripts/preflight.py --skip-gates    # 只做数据体检，不跑三道门
退出码：0 = GO（或有 WARN 但可开训）；1 = NO-GO（必须修）。
"""
import csv
import json
import pathlib
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
TRAIN = ROOT / "data" / "train" / "images"
VAL = ROOT / "data" / "val"
CSV = ROOT / "data" / "provenance.csv"
THEME_MIN = {"ritual": 8, "court": 8, "nature": 8, "water": 8, "ornament": 6}
THEME_SOFT = {"machine_or_sky"}

# SPEC §5.2：短边默认门槛 768；8GB 剖面可放到 640（不得低于 640）。
# 实际门槛取该剖面 resolution_buckets 的最小值，与 make_kohya_structure.py 保持一致。
FALLBACK_MIN_SHORT = {"8gb": 640, "16gb": 768}


def profile_min_short(profile):
    y = ROOT / "hardware" / ("%s.yaml" % profile)
    try:
        import yaml
        d = yaml.safe_load(y.read_text(encoding="utf-8")) or {}
        buckets = (d.get("train") or {}).get("resolution_buckets") or []
        if buckets:
            return int(min(buckets)), "%s 剖面 resolution_buckets 最小值" % profile
    except Exception:
        pass
    return FALLBACK_MIN_SHORT.get(profile, 768), "内置默认（未读到 yaml）"

errors, warns = [], []


def err(msg):
    errors.append(msg)
    print("  [FAIL] %s" % msg)


def warn(msg):
    warns.append(msg)
    print("  [WARN] %s" % msg)


def ok(msg):
    print("  [OK]   %s" % msg)


def check_triplets():
    print("== 1. 三件套完整性 ==")
    pngs = sorted(TRAIN.glob("*.png"))
    if not pngs:
        err("data/train/images 下没有训练图")
        return []
    bad = []
    for p in pngs:
        for ext in (".txt", ".json"):
            if not p.with_suffix(ext).exists():
                bad.append("%s 缺 %s" % (p.name, ext))
    if bad:
        for b in bad:
            err(b)
    else:
        ok("%d 张三件套齐全（png + txt + json）" % len(pngs))
    return pngs


def check_schema(pngs):
    print("== 2. json 结构与 split ==")
    themes, bad = {}, []
    for p in pngs:
        jf = p.with_suffix(".json")
        try:
            d = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as exc:
            bad.append("%s 解析失败 %s" % (jf.name, exc))
            continue
        if d.get("split") != "train":
            err("%s split=%r，训练集里只应有 train" % (jf.name, d.get("split")))
        for key in ("family", "theme", "style", "content", "caption_en"):
            if key not in d:
                bad.append("%s 缺字段 %s" % (jf.name, key))
        th = (d.get("theme") or {}).get("primary")
        if th:
            themes[th] = themes.get(th, 0) + 1
    if bad:
        for b in bad:
            err(b)
    else:
        ok("json 字段齐全且 split 均为 train")
    return themes


def check_quota(themes):
    print("== 3. theme 配额（§3.3）==")
    print("  分布：%s" % themes)
    for t, need in THEME_MIN.items():
        got = themes.get(t, 0)
        if got < need:
            err("%s %d/%d，未达硬配额" % (t, got, need))
    for t in THEME_SOFT:
        got = themes.get(t, 0)
        if got < THEME_MIN.get(t, 0):
            warn("%s %d，软配额未达（SPEC §3.3 允许保留）" % (t, got))
    if not errors:
        ok("硬配额全部达标")


def check_size(pngs, min_short, note):
    print("== 4. 短边门槛（§5.2，>= %d，%s）==" % (min_short, note))
    try:
        from PIL import Image
    except Exception:
        warn("Pillow 未安装，跳过尺寸检查（pip install Pillow）")
        return
    small = []
    for p in pngs:
        with Image.open(p) as im:
            w, h = im.size
        if min(w, h) < min_short:
            small.append("%s %dx%d" % (p.name, w, h))
    if small:
        for s in small:
            err("短边不足：%s" % s)
    else:
        ok("全部达标")


def check_ledger(pngs):
    print("== 5. 册/图双向链接（§0.3）==")
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    by_file = {r["train_filename"]: r for r in rows if r.get("train_filename")}
    orphan_img, bad_decision = [], []
    for p in pngs:
        r = by_file.get(p.name)
        if r is None:
            orphan_img.append(p.name)
            continue
        if r.get("decision") != "train":
            bad_decision.append("%s -> decision=%s" % (p.name, r.get("decision")))
        if (r.get("license") or "").upper() not in ("PD", "CC0"):
            bad_decision.append("%s -> license=%s" % (p.name, r.get("license")))
    if orphan_img:
        for o in orphan_img:
            err("训练图无 provenance 记录（没记录=不存在）：%s" % o)
    for b in bad_decision:
        err(b)
    ghost = [f for f in by_file if not (TRAIN / f).exists() and not (VAL / f).exists()]
    for g in ghost:
        warn("册里有 train_filename=%s 但图不在 train/val 下" % g)
    if not orphan_img and not bad_decision:
        ok("每张训练图都有 train 记录且许可为 PD/CC0")


def check_val():
    print("== 6. val 集（§6.1，4–6 张且未混入训练）==")
    vp = sorted(VAL.glob("*.png")) if VAL.is_dir() else []
    if not VAL.is_dir():
        warn("无 data/val/ 目录——§6.1 要求留 4–6 张不参与训练")
        return
    if not (4 <= len(vp) <= 6):
        warn("val %d 张，§6.1 要求 4–6 张" % len(vp))
    bad = []
    for p in vp:
        jf = p.with_suffix(".json")
        if not jf.exists():
            bad.append("%s 缺 json" % p.name)
            continue
        d = json.loads(jf.read_text(encoding="utf-8"))
        if d.get("split") != "val":
            bad.append("%s split=%r" % (p.name, d.get("split")))
        if (TRAIN / p.name).exists():
            err("%s 同时出现在 train 与 val" % p.name)
    for b in bad:
        err(b)
    if not bad:
        ok("val %d 张，split=val，未混入训练集" % len(vp))


def check_metadata(pngs):
    print("== 7. metadata.json 条数 ==")
    mp = TRAIN / "metadata.json"
    if not mp.exists():
        warn("未生成 metadata.json，跑 make_kohya_structure.py 生成")
        return
    try:
        md = json.loads(mp.read_text(encoding="utf-8"))
    except Exception as exc:
        err("metadata.json 解析失败 %s" % exc)
        return
    if len(md) != len(pngs):
        err("metadata %d 条 vs 训练图 %d 张，需重跑 make_kohya_structure" % (len(md), len(pngs)))
    else:
        ok("metadata %d 条，与训练图一致" % len(md))


def run_gates(profile):
    print("== 8. 三道门 ==")
    gates = [
        ("license_gate", [sys.executable, "scripts/license_gate.py", "--csv", "data/provenance.csv"]),
        ("caption_lint", [sys.executable, "scripts/caption_lint.py", "--train", "data/train/images"]),
        ("make_kohya_structure", [sys.executable, "scripts/make_kohya_structure.py",
                                  "--profile", profile]),
    ]
    for name, cmd in gates:
        r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode == 0:
            ok("%s EXIT=0" % name)
        else:
            err("%s EXIT=%d" % (name, r.returncode))
            tail = (r.stdout or "").strip().splitlines()[-4:]
            for line in tail:
                print("        | %s" % line)


def main():
    import argparse as _ap
    p = _ap.ArgumentParser(description="decomineral 训练前自检")
    p.add_argument("--profile", default="8gb")
    p.add_argument("--skip-gates", action="store_true")
    args = p.parse_args()

    print("=" * 60)
    print("preflight（profile=%s）" % args.profile)
    print("=" * 60)
    pngs = check_triplets()
    if pngs:
        themes = check_schema(pngs)
        check_quota(themes)
        min_short, note = profile_min_short(args.profile)
        check_size(pngs, min_short, note)
        check_ledger(pngs)
        check_val()
        check_metadata(pngs)
    if not args.skip_gates:
        run_gates(args.profile)

    print("-" * 60)
    if errors:
        print("结果：NO-GO（%d 项必须修，%d 项警告）" % (len(errors), len(warns)))
        return 1
    print("结果：GO（%d 项警告，不阻塞开训）" % len(warns))
    return 0


if __name__ == "__main__":
    sys.exit(main())
