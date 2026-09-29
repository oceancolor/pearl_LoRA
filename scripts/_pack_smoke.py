#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_pack_smoke.py — 打包「GPU 机冒烟最小集」，避免为验证链路传 370MB 全量数据集。

只带：脚本 / 配置 / schema / prompts / provenance.csv + 前 N 张三件套。
目标机解压后跑 make_kohya_structure.py 会按实际图片数重写 metadata.json。

用法：
    python scripts/_pack_smoke.py                # 默认 6 张
    python scripts/_pack_smoke.py --n 8
产物：smoke_pack.tar.gz（仓库根）
"""
import argparse
import pathlib
import tarfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
IMAGES = ROOT / "data" / "train" / "images"
OUT = ROOT / "smoke_pack.tar.gz"

DIRS = ["scripts", "configs", "schema", "hardware", "prompts"]
FILES = ["SPEC.md", "CODEBUDDY.md", ".gitignore", "data/provenance.csv"]

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=6, help="带几张三件套（默认 6）")
args = ap.parse_args()

pngs = sorted(IMAGES.glob("*.png"))[: args.n]
if not pngs:
    raise SystemExit("data/train/images 下没有训练图")

paths = []
for d in DIRS:
    p = ROOT / d
    if p.exists():
        paths += [f for f in p.rglob("*") if f.is_file() and "__pycache__" not in f.parts]
for f in FILES:
    p = ROOT / f
    if p.exists():
        paths.append(p)
for im in pngs:
    paths.append(im)
    for ext in (".txt", ".json"):
        q = im.with_suffix(ext)
        if q.exists():
            paths.append(q)

with tarfile.open(OUT, "w:gz") as tar:
    for p in paths:
        tar.add(p, arcname=str(p.relative_to(ROOT)))

mb = OUT.stat().st_size / 1024 / 1024
print("打包 %d 个文件 -> %s（%.1f MB）" % (len(paths), OUT.name, mb))
print("训练图：%s" % ", ".join(p.name for p in pngs))
print("生成于 %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
