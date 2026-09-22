import pathlib
from PIL import Image

RAW = pathlib.Path("data/inbox/raw")
OUT = pathlib.Path("data/crops/_review")
fid = "met_42716"
src = next((p for n in ("image.jpg", "image.jpeg", "image.png")
            if (p := RAW / fid / n).exists()), None)
im = Image.open(src).convert("RGB")
w, h = im.size
im.thumbnail((360, 360))
im.save(OUT / (fid + "_w.jpg"), quality=65)
print(fid, "%dx%d" % (w, h))
