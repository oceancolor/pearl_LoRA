"""列出概念目录里的非 png 图片尺寸：python scripts/_size.py <目录>"""
import pathlib
import sys

from PIL import Image

d = pathlib.Path(sys.argv[1])
for p in sorted(d.iterdir()):
    if p.suffix.lower() not in (".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".png"):
        continue
    if p.suffix.lower() == ".png" and p.with_suffix(".txt").exists():
        continue
    im = Image.open(p)
    w, h = im.size
    print("%-12s %5dx%-5d %-5s short=%-5d %s" % (p.name, w, h, im.mode, min(w, h),
                                                "OK" if min(w, h) >= 768 else "SMALL(<768)"))
