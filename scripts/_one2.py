import pathlib
from PIL import Image

RAW = pathlib.Path("data/inbox/raw")
OUT = pathlib.Path("data/crops/_review")
for fid in ["commons_17_jpg", "commons_K_rin_Matsushima_jpg"]:
    src = next((p for n in ("image.jpg", "image.jpeg", "image.png", "image.webp")
                if (p := RAW / fid / n).exists()), None)
    if not src:
        print(fid, "NO FILE")
        continue
    im = Image.open(src).convert("RGB")
    w, h = im.size
    im.thumbnail((360, 360))
    im.save(OUT / (fid[-18:] + "_w.jpg"), quality=65)
    print(fid, "%dx%d" % (w, h), "->", fid[-18:] + "_w.jpg")
