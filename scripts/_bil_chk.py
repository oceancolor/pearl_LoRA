import pathlib
from PIL import Image

RAW = pathlib.Path("data/inbox/raw")
for d in sorted(RAW.iterdir()):
    if not d.name.startswith("commons_Ivan_Bilibin"):
        continue
    src = next((p for n in ("image.jpg", "image.jpeg", "image.png")
                if (p := d / n).exists()), None)
    if not src:
        print(d.name, "NO FILE")
        continue
    with Image.open(src) as im:
        w, h = im.size
    print("%-70s %dx%d short=%d %s" % (d.name, w, h, min(w, h),
                                       "OK" if min(w, h) >= 640 else "SMALL"))
