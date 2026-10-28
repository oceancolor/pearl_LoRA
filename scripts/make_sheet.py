#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_sheet.py — 把一批图拼成一张联系表，便于在无法拷贝文件的环境里截图查看。

用途：共享存储只能预览、不能下载时，用它生成一张总图，截图发给协作者即可完成目检。

  python scripts/make_sheet.py <图片目录> <输出.jpg> [--cols N] [--cell N]
  python scripts/make_sheet.py eval_concept/ritual /tmp/sheet_ritual.jpg

文件名会标在每个格子上方（取文件名中的时间戳部分）。
"""
import argparse
import pathlib
import sys

from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--cell", type=int, default=340)
    a = ap.parse_args()

    files = sorted(p for p in pathlib.Path(a.src).rglob("*")
                   if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    if not files:
        sys.exit("目录里没有图片: %s" % a.src)

    cell, cols = a.cell, a.cols
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 18)), (26, 26, 26))
    draw = ImageDraw.Draw(sheet)

    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB")
        im.thumbnail((cell, cell))
        x = (i % cols) * cell
        y = (i // cols) * (cell + 18)
        sheet.paste(im, (x + (cell - im.width) // 2, y + 18 + (cell - im.height) // 2))
        # 标签：只取文件名里的序号/时间戳，短一些
        lab = f.stem.replace("image_", "").replace("_000", "")
        draw.text((x + 4, y + 3), lab[-20:], fill=(255, 215, 110))

    out = pathlib.Path(a.dst)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=80)
    print("%s  %dx%d  共 %d 张" % (out, sheet.width, sheet.height, len(files)))


if __name__ == "__main__":
    main()
