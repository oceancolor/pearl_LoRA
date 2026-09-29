"""_fix16.py — 为 16gb 剖面（SPEC §5.2 短边 >=768）修补数据。

1) 00007 重裁（原图 775x949，旧裁短边 767）→ 写回 data/train/images/00007.png
2) 00050 新增（光琳《松岛图》，替换短边不足的 00024）
仅做裁切与写图，不写 provenance（交 _triage.py / _recover_fill.py）。
"""
import pathlib
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "inbox" / "raw"
IMG = ROOT / "data" / "train" / "images"
OUT = ROOT / "data" / "crops" / "_review"

JOBS = [
    ("00007", "commons_TsangMonk_jpg", (0, 12, 775, 937)),
    ("00050", "commons_K_rin_Matsushima_jpg", (10, 10, 1425, 1378)),
]

for num, fid, box in JOBS:
    src = next((p for n in ("image.jpg", "image.jpeg", "image.png")
                if (p := RAW / fid / n).exists()), None)
    if not src:
        print(num, "NO FILE")
        continue
    im = Image.open(src)
    w, h = im.size
    c = im.convert("RGB")
    if box:
        box = (max(0, box[0]), max(0, box[1]), min(w, box[2]), min(h, box[3]))
        c = c.crop(box)
    print("%s <- %s 原图 %dx%d 裁 %s -> %dx%d 短边=%d %s" % (
        num, fid, w, h, box, c.width, c.height, min(c.size),
        "OK(>=768)" if min(c.size) >= 768 else "FAIL"))
    c.save(IMG / ("%s.png" % num))
    c.copy().thumbnail((360, 360))
    c.save(OUT / ("%s_w.jpg" % num), quality=65)
