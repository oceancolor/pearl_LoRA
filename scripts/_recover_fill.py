"""崩溃恢复：把 data/crops/_ingest_map.csv 的入库映射回填进 provenance.csv 的 train_filename。

只动 train_filename / family / theme_primary 三列，且仅对映射命中的行；
family / theme_primary 取 data/train/images/<id>.json 的实际标注（SPEC §0.3 三件套↔provenance 必须一致）。
幂等：重复运行结果相同。
"""
import csv
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "provenance.csv"
MAP = ROOT / "data" / "crops" / "_ingest_map.csv"
IMG = ROOT / "data" / "train" / "images"

FAM_CODE = {
    "silkroad_mural": "A",
    "persian_miniature": "B",
    "bilibin": "C",
    "clarkestain": "D",
    "rimpa": "E",
    "pure_ornament": "F",
    "other_pd": "G",
}

# file_id -> (train_filename, family_code, theme_primary)
want = {}
with MAP.open(encoding="utf-8") as f:
    for row in csv.reader(f):
        if len(row) != 2:
            continue
        num, file_id = row[0].strip(), row[1].strip()
        meta = json.loads((IMG / f"{num}.json").read_text(encoding="utf-8"))
        want[file_id] = (
            f"{num}.png",
            FAM_CODE[meta["family"]],
            meta["theme"]["primary"],
        )

# 已入库但不在 map 里的早期三件套：同样按 json 校正 family/theme
with CSV.open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))
    fieldnames = list(rows[0].keys())

changed = []
for r in rows:
    fid = r["file_id"]
    tf = r["train_filename"].strip()
    if fid in want:
        new_tf, fam, theme = want[fid]
    elif tf:
        num = pathlib.Path(tf).stem
        jf = IMG / f"{num}.json"
        if not jf.exists():
            continue
        meta = json.loads(jf.read_text(encoding="utf-8"))
        new_tf, fam, theme = tf, FAM_CODE[meta["family"]], meta["theme"]["primary"]
    else:
        continue

    before = (r["train_filename"], r["family"], r["theme_primary"])
    after = (new_tf, fam, theme)
    if before != after:
        r["train_filename"], r["family"], r["theme_primary"] = after
        changed.append((fid, before, after))

with CSV.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)

for fid, before, after in changed:
    print(f"{fid}: {before} -> {after}")
print(f"共更新 {len(changed)} 行 / 总 {len(rows)} 行")
