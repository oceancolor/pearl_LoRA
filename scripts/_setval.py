import json
import pathlib

VAL = pathlib.Path("data/val")
for jf in sorted(VAL.glob("*.json")):
    d = json.loads(jf.read_text(encoding="utf-8"))
    d["split"] = "val"
    jf.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(jf.name, d["id"], d["family"], d["theme"]["primary"], d["split"])
