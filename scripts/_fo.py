import pathlib
from PIL import Image

RAW = pathlib.Path("data/inbox/raw")
OUT = pathlib.Path("data/crops/_review")
n = 0
for d in sorted(RAW.iterdir()):
    if "Fire_Ordeal" not in d.name:
        continue
    src = next((p for n2 in ("image.jpg", "image.jpeg", "image.png")
                if (p := d / n2).exists()), None)
    if not src:
        print("NOFILE", d.name)
        continue
    im = Image.open(src).convert("RGB")
    w, h = im.size
    n += 1
    im.thumbnail((320, 320))
    name = "F%d.jpg" % n
    im.save(OUT / name, quality=65)
    print("%-58s %dx%d -> %s" % (d.name[:58], w, h, name))
