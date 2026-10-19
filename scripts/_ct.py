"""概念集候选缩略图：python scripts/_ct.py <file_id> [<file_id> ...]

输出到 data/crops/_review/<file_id>_w.jpg，并打印原图尺寸与短边是否达 768（16gb 剖面门槛）。
"""
import pathlib
import sys

from PIL import Image

RAW = pathlib.Path("data/inbox/raw")
OUT = pathlib.Path("data/crops/_review")
OUT.mkdir(parents=True, exist_ok=True)

MIN_SHORT = 768  # §5.2，16gb 剖面

if not sys.argv[1:]:
    # 无参数：列出 inbox/raw 全部候选的尺寸与是否达标（不出缩略图）
    print("== inbox/raw 全部候选（短边门槛 %d）==\n" % MIN_SHORT)
    ok = []
    for d in sorted(p for p in RAW.iterdir() if p.is_dir()):
        src = next((p for n in ("image.jpg", "image.jpeg", "image.png", "image.webp")
                    if (p := d / n).exists()), None)
        if not src:
            print("%-72s NO FILE" % d.name[:72])
            continue
        w, h = Image.open(src).size
        short = min(w, h)
        good = short >= MIN_SHORT
        if good:
            ok.append(d.name)
        print("%-72s %5dx%-5d short=%-5d %s" % (d.name[:72], w, h, short,
                                                "OK" if good else "SMALL"))
    print("\n达标 %d 个：\n%s" % (len(ok), "\n".join(ok)))
    sys.exit(0)

for fid in sys.argv[1:]:
    src = next((p for n in ("image.jpg", "image.jpeg", "image.png", "image.webp")
                if (p := RAW / fid / n).exists()), None)
    if not src:
        print("%s  NO FILE" % fid)
        continue
    im = Image.open(src)
    w, h = im.size
    short = min(w, h)
    thumb = im.convert("RGB")
    thumb.thumbnail((420, 420))
    thumb.save(OUT / ("%s_w.jpg" % fid[:70]), quality=72)
    print("%s  %dx%d  short=%d  %s" % (fid[:70], w, h, short,
                                       "OK" if short >= MIN_SHORT else "SMALL(<768)"))
