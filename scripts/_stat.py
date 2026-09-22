import csv
import json
import pathlib

rows = list(csv.DictReader(open("data/provenance.csv", encoding="utf-8")))
print("provenance 总行:", len(rows))
from collections import Counter
print("decision:", dict(Counter(r["decision"] for r in rows)))

IMG = pathlib.Path("data/train/images")
VAL = pathlib.Path("data/val")
th, fam = Counter(), Counter()
for p in sorted(IMG.glob("*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    if "theme" not in d:
        print("缺 theme 字段:", p.name)
        continue
    th[d["theme"]["primary"]] += 1
    fam[d["family"]] += 1
print("train 张数:", len(list(IMG.glob("*.png"))))
print("train theme:", dict(th))
print("train family:", dict(fam))
vt = Counter()
for p in sorted(VAL.glob("*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    vt[d["theme"]["primary"]] += 1
print("val 张数:", len(list(VAL.glob("*.png"))), "theme:", dict(vt))
