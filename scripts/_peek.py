"""放大看单张（长边 900），用于定裁切框与写 caption。
python scripts/_peek.py <file_id> [l t r b]   # 可选裁切框（0–1 比例），预览裁后效果
"""
import pathlib
import sys

from PIL import Image

Image.MAX_IMAGE_PIXELS = None
fid = sys.argv[1]
d = pathlib.Path("data/inbox/raw") / fid
src = next(p for n in ("image.jpg", "image.png", "image.jpeg") if (p := d / n).exists())
im = Image.open(src).convert("RGB")
if len(sys.argv) == 6:
    l, t, r, b = map(float, sys.argv[2:6])
    w, h = im.size
    im = im.crop((int(l * w), int(t * h), int(r * w), int(b * h)))
im.thumbnail((900, 900))
dst = pathlib.Path("data/crops/_review") / ("peek_%s.jpg" % fid[:40])
im.save(dst, quality=85)
print(dst, im.size)
