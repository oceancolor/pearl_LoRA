import pathlib
from PIL import Image

RAW = pathlib.Path("data/inbox/raw")
IDS = [
    "commons_Boats_upon_Waves_MET_DP262129_jpg",
    "commons_Boats_upon_Waves_MET_DP262130_jpg",
    "commons_17_jpg",
    "commons_The_Enthronement_of_King_Luhrasp_Iran_17th_century_jpg",
    "commons_Iranian_Courtiers_of_Shah_Abbas_I_Walters_W691A_jpg",
    "commons_Binding_for_the_Mantiq_al_tayr_Language_of_the_Birds_MET_DP2",
]
for fid in IDS:
    src = next((p for n in ("image.jpg", "image.jpeg", "image.png", "image.webp")
                if (p := RAW / fid / n).exists()), None)
    if not src:
        print(fid[:50], "NO FILE")
        continue
    with Image.open(src) as im:
        w, h = im.size
    print("%-52s %dx%d short=%d %s" % (fid[:52], w, h, min(w, h),
                                       "OK" if min(w, h) >= 640 else "SMALL"))
