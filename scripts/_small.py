import pathlib
from PIL import Image

OUT = pathlib.Path("data/crops/_review")
for n in ["00045", "00046", "00047", "00048", "00049"]:
    p = OUT / ("%s_w.jpg" % n)
    im = Image.open(p)
    im.thumbnail((360, 360))
    im.save(OUT / ("%s_s.jpg" % n), quality=60)
    print(n, im.size)
