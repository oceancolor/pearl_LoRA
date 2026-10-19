"""拼接联系表，一次看图替代逐张看。

python scripts/_sheet.py <输出名> <图片目录> [起始编号] [张数]
例：python scripts/_sheet.py future data/concept_later/future_seed 6 6
"""
import pathlib
import sys

from PIL import Image, ImageDraw

out_name = sys.argv[1]
src_dir = pathlib.Path(sys.argv[2])
start = int(sys.argv[3]) if len(sys.argv) > 3 else 1
count = int(sys.argv[4]) if len(sys.argv) > 4 else 12

files = sorted(src_dir.glob("*.png"))[start - 1:start - 1 + count]
CELL = 300
cols = 3
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols * CELL, rows * (CELL + 18)), (28, 28, 28))
draw = ImageDraw.Draw(sheet)

for i, f in enumerate(files):
    im = Image.open(f).convert("RGB")
    im.thumbnail((CELL, CELL))
    x = (i % cols) * CELL
    y = (i // cols) * (CELL + 18)
    sheet.paste(im, (x + (CELL - im.width) // 2, y + 18 + (CELL - im.height) // 2))
    draw.text((x + 4, y + 3), f.stem, fill=(255, 220, 120))

dst = pathlib.Path("data/crops/_review") / ("sheet_%s.jpg" % out_name)
sheet.save(dst, quality=82)
print(dst, sheet.size, "cells=%d" % len(files))
