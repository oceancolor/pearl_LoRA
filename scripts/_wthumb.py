import pathlib
from PIL import Image

RAW = pathlib.Path("data/inbox/raw")
OUT = pathlib.Path("data/crops/_review")
OUT.mkdir(parents=True, exist_ok=True)
IDS = [
    "commons_IO_Islamic_2448_f_65v_jpg",
    "commons_Sadi7_jpg",
    "commons_Tang_4_jpg",
]

for fid in IDS:
    src = next((p for n in ("image.jpg", "image.png", "image.jpeg")
                if (p := RAW / fid / n).exists()), None)
    if not src:
        print(fid, "NO FILE")
        continue
    im = Image.open(src)
    w, h = im.size
    im = im.convert("RGB")
    im.thumbnail((480, 480))
    im.save(OUT / (fid[:80] + "_w.jpg"), quality=72)
    print(fid[:80], w, h, "short", min(w, h))
