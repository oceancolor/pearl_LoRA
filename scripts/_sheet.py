"""拼接联系表，一次看图替代逐张看。

  python scripts/_sheet.py <输出名> <目录> [起始] [张数] [--cell N --cols N]
  python scripts/_sheet.py <输出名> <图片1> <图片2> ...
"""
import pathlib
import sys

from PIL import Image, ImageDraw

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opts = {}
for a in sys.argv[1:]:
    if a.startswith("--"):
        k, _, v = a[2:].partition("=")
        opts[k] = int(v or 0)

out_name = args[0]
first = pathlib.Path(args[1])

if first.is_dir():
    start = int(args[2]) if len(args) > 2 else 1
    count = int(args[3]) if len(args) > 3 else 12
    root = first.resolve()
    allf = [f for f in sorted(first.rglob("*"))
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
            and f.resolve().parent.parent == root]
    allf.sort()
    files = allf[start - 1:start - 1 + count]
else:
    files = [pathlib.Path(a) for a in args[1:]]

if not files:
    sys.exit("没有可用图片")

CELL = opts.get("cell", 300)
cols = opts.get("cols", 3)
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols * CELL, rows * (CELL + 16)), (28, 28, 28))
draw = ImageDraw.Draw(sheet)

for i, f in enumerate(files):
    try:
        im = Image.open(f).convert("RGB")
    except Exception:
        continue
    im.thumbnail((CELL, CELL))
    x = (i % cols) * CELL
    y = (i // cols) * (CELL + 16)
    sheet.paste(im, (x + (CELL - im.width) // 2, y + 16 + (CELL - im.height) // 2))
    draw.text((x + 3, y + 2), f.parent.name[-8:] if f.parent.name != "image" else f.stem[:10],
              fill=(255, 220, 120))

dst = pathlib.Path("data/crops/_review") / ("sheet_%s.jpg" % out_name)
sheet.save(dst, quality=80)
print(dst, sheet.size, "cells=%d" % len(files))
