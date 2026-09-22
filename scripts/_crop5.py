"""_crop5.py — 第三轮 5 张入库图的裁切（SPEC §5.3：裁去纸边/装裱边/文字栏，只留画幅）。

坐标是原图像素框 (left, top, right, bottom)，按目检估算；裁完出缩略图到
data/crops/_review/ 供人工复核（本脚本不写 provenance，入册由后续步骤做）。
"""
import pathlib
import sys

from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "inbox" / "raw"
OUT = ROOT / "data" / "crops" / "_review"
OUT.mkdir(parents=True, exist_ok=True)

# num -> (file_id, 原图文件, bbox)
JOBS = [
    ("00017", "met_451289", "image.jpg", (200, 60, 2550, 3900)),
    ("00018", "met_451726", "image.jpg", (550, 930, 2460, 3320)),
    ("00019", "met_451403", "image.jpg", (150, 150, 3680, 2613)),
    ("00020", "met_452651", "image.jpg", (320, 1720, 2470, 3010)),
    ("00021", "commons_Zal_and_the_Simurgh_ink_and_opaque_watercolor_painting_from",
     "image.jpg", (100, 500, 1495, 2110)),
]

for num, fid, fname, box in JOBS:
    src = RAW / fid / fname
    if not src.exists():
        print("  ! %s 缺原图 %s" % (fid, src))
        continue
    im = Image.open(src)
    w, h = im.size
    box = (max(0, box[0]), max(0, box[1]), min(w, box[2]), min(h, box[3]))
    cropped = im.convert("RGB").crop(box)
    print("%s <- %s  orig %dx%d  crop %s -> %dx%d  short=%d %s" % (
        num, fid, w, h, box, cropped.width, cropped.height,
        min(cropped.width, cropped.height),
        "OK" if min(cropped.width, cropped.height) >= 640 else "SMALL"))
    cropped.save(OUT / ("%s_%s_crop.jpg" % (num, fid)), quality=85)
    cropped.copy().thumbnail((760, 760))
    cropped.save(OUT / ("%s_w.jpg" % num), quality=82)
