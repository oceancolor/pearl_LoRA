import csv

CSV = "data/provenance.csv"
VAL_FILES = {
    "commons_Mogao_Cave_288_Devatas_at_the_Balcony_Western_Wei_period_jpg": "00006",
    "met_448280": "00011",
    "met_891632": "00015",
    "commons_16_2_8_2005_Noahs_ark_Hafis_Abru_2_jpg": "00023",
    "commons_KorinsScreen_webp": "00044",
}
rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
fields = list(rows[0].keys())
for r in rows:
    if r["file_id"] in VAL_FILES and "val" not in r["decision_reason"]:
        r["decision_reason"] = r["decision_reason"] + "【val 集：%s.png 已移入 data/val/，不参与训练，只作抽检对照（§6.1）】" % VAL_FILES[r["file_id"]]
with open(CSV, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
print("已标注 val 集 %d 条" % len(VAL_FILES))
