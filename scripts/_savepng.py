import pathlib
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "inbox" / "raw"
IMG = ROOT / "data" / "train" / "images"
BOX = {
    "00017": ("met_451289", (200, 60, 2550, 3900)),
    "00018": ("met_451726", (550, 930, 2460, 3320)),
    "00019": ("met_451403", (150, 150, 3680, 2613)),
    "00020": ("met_452651", (320, 1720, 2470, 3010)),
    "00021": ("commons_Zal_and_the_Simurgh_ink_and_opaque_watercolor_painting_from",
              (100, 500, 1495, 2110)),
}

for num, (fid, box) in BOX.items():
    src = RAW / fid / "image.jpg"
    im = Image.open(src).convert("RGB").crop(box)
    dst = IMG / ("%s.png" % num)
    im.save(dst)
    print(num, fid, im.size)

