import json
import pathlib

IMG = pathlib.Path("data/train/images")
for n in ["00050"]:
    txt = (IMG / (n + ".txt")).read_text(encoding="utf-8").strip()
    jf = IMG / (n + ".json")
    d = json.loads(jf.read_text(encoding="utf-8"))
    d["caption_en"] = txt
    jf.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(n, len(txt))
