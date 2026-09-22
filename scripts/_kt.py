import pathlib
from PIL import Image

RAW = pathlib.Path("data/inbox/raw")
OUT = pathlib.Path("data/crops/_review")
OUT.mkdir(parents=True, exist_ok=True)
for d in sorted(RAW.iterdir()):
    if "Kalila_Upbraiding" not in d.name:
        continue
    src = next((p for n in ("image.jpg", "image.jpeg", "image.png", "image.webp")
                if (p := d / n).exists()), None)
    if not src:
        print(d.name, "NO FILE")
        continue
    im = Image.open(src).convert("RGB")
    w, h = im.size
    im.thumbnail((360, 360))
    out = OUT / ("K_" + d.name[-28:] + ".jpg")
    im.save(out, quality=65)
    print(d.name, "%dx%d" % (w, h), "->", out.name)
