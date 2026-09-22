import pathlib
from PIL import Image

RAW = pathlib.Path("data/inbox/raw")
OUT = pathlib.Path("data/crops/_review")
for d in sorted(RAW.iterdir()):
    if "Banner_with_Bodhisattva" not in d.name:
        continue
    src = next((p for n in ("image.jpg", "image.jpeg", "image.png")
                if (p := d / n).exists()), None)
    if not src:
        continue
    im = Image.open(src).convert("RGB")
    w, h = im.size
    im.thumbnail((320, 320))
    name = "B_" + d.name[-22:] + ".jpg"
    im.save(OUT / name, quality=65)
    print("%-58s %dx%d -> %s" % (d.name, w, h, name))
