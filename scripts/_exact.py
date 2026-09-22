import json
import pathlib

RAW = pathlib.Path("data/inbox/raw")
KEYS = ["Binding_for_the_Mantiq", "Kalila_Upbraiding", "Fire_Ordeal_of_Siyawush"]
for d in sorted(RAW.iterdir()):
    if not any(k in d.name for k in KEYS):
        continue
    m = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    print("[%s]" % d.name)
    print("  lic=%s pub=%r" % (m.get("license"), m.get("publication_year")))
