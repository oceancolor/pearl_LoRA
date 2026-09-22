import pathlib
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "inbox" / "raw"
IMG = ROOT / "data" / "train" / "images"
OUT = ROOT / "data" / "crops" / "_review"
OUT.mkdir(parents=True, exist_ok=True)
BOX = {
    "00045": ("commons_Boats_upon_Waves_MET_DP262129_jpg", (20, 400, 1440, 1700)),
    "00046": ("commons_Binding_for_the_Mantiq_al_tayr_Language_of_the_Birds_MET_DP2", (200, 220, 2420, 3700)),
    "00047": ("commons_Iranian_Courtiers_of_Shah_Abbas_I_Walters_W691A_jpg", (108, 130, 1022, 1712)),
    "00048": ("commons_Kalila_Upbraiding_Dimna_Folio_from_a_Kalila_wa_Dimna_MET_DP", (380, 880, 2480, 3520)),
    "00049": ("commons_The_Fire_Ordeal_of_Siyawush_from_a_Shahnama_of_Firdawsi_Safa", (140, 1000, 1870, 2260)),


}

for num, (fid, box) in BOX.items():
    src = next((p for n in ("image.jpg", "image.jpeg", "image.png")
                if (p := RAW / fid / n).exists()), None)
    im = Image.open(src)
    w, h = im.size
    c = im.convert("RGB").crop(box)
    c.save(IMG / ("%s.png" % num))
    print(num, fid, "%dx%d" % (w, h), "->", c.size, "short", min(c.size))
    c.copy().thumbnail((480, 480))
    c.save(OUT / ("%s_w.jpg" % num), quality=72)

