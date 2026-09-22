import json
import pathlib

RAW = pathlib.Path("data/inbox/raw")
KEYS = ["Boats_upon_Waves_MET_DP262129", "Binding_for_the_Mantiq",
        "Iranian_Courtiers_of_Shah_Abbas", "Tang_4_jpg", "Kalila_Upbraiding_Dimna_Folio_from_a_Kalila_wa_Dimna_MET_DP"]
for d in sorted(RAW.iterdir()):
    if not any(k in d.name for k in KEYS):
        continue
    m = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    print("%s\n  lic=%s creator=%r death=%r pub=%r\n  page=%s" % (
        d.name, m.get("license"), m.get("creator"), m.get("creator_death_year"),
        m.get("publication_year"), m.get("page_url")))
