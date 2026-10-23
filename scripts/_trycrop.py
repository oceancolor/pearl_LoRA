"""批量试裁：python scripts/_trycrop.py <输出名> id:l,t,r,b [id:l,t,r,b ...]
每张按比例裁切后缩到 600 宽拼成联系表，并打印裁后（长边 1600 降采样后）短边。
"""
import pathlib
import sys

from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
RAW = pathlib.Path("data/inbox/raw")
CELL = 440
out = sys.argv[1]
tiles = []
for spec in sys.argv[2:]:
    fid, box = spec.split(":")
    l, t, r, b = map(float, box.split(","))
    src = next(p for n in ("image.jpg", "image.png") if (p := RAW / fid / n).exists())
    im = Image.open(src).convert("RGB")
    w, h = im.size
    im = im.crop((int(l * w), int(t * h), int(r * w), int(b * h)))
    cw, ch = im.size
    s = 1600 / max(cw, ch) if max(cw, ch) > 1600 else 1
    short = int(min(cw, ch) * s)
    print("%-12s crop=%dx%d -> short=%d %s" % (fid, cw, ch, short, "OK" if short >= 768 else "SMALL"))
    im.thumbnail((CELL, CELL))
    tiles.append((fid, im))

cols = 2
rows = (len(tiles) + 1) // 2
sheet = Image.new("RGB", (cols * CELL, rows * (CELL + 16)), (28, 28, 28))
d = ImageDraw.Draw(sheet)
for i, (fid, im) in enumerate(tiles):
    x, y = (i % cols) * CELL, (i // cols) * (CELL + 16)
    sheet.paste(im, (x + (CELL - im.width) // 2, y + 16 + (CELL - im.height) // 2))
    d.text((x + 3, y + 2), fid, fill=(255, 220, 120))
dst = pathlib.Path("data/crops/_review") / ("try_%s.jpg" % out)
sheet.save(dst, quality=82)
print(dst)
