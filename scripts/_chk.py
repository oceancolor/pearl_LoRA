import csv
rows = list(csv.DictReader(open("data/provenance.csv", encoding="utf-8")))
for r in rows:
    if "Boats_upon" in r["file_id"]:
        print(r["file_id"], r["creator_death_year"], r["decision"])
