"""概念 LoRA 预筛：列出训练集每张的 family/theme/content，供人工挑选各概念候选。

只做只读统计，不改动任何数据。
"""
import json
import pathlib

IMG = pathlib.Path("data/train/images")

# 各概念的关键词（用于自动打分提示，最终仍需人工看图确认）
HINT = {
    "deco_ritual": ("canopy", "altar", "bodhisattva", "throne", "attendant",
                    "devotee", "guardian", "banner", "halo", "lotus", "sacred"),
    "deco_water": ("wave", "water", "boat", "fish", "pool", "sea", "lotus",
                   "islet", "crest", "swimmer", "ark"),
    # deco_future = 幻想（非科幻）：天宫、云、异兽、神鸟、星象、塔幢、楼阁
    "deco_future": ("tower", "pillar", "palace", "cloud", "dragon", "bird",
                    "simurgh", "wing", "star", "sky", "serpent", "flame",
                    "crown", "islet", "terrace", "pavilion", "canopy"),
}

rows = []
for p in sorted(IMG.glob("*.json")):
    if p.name == "metadata.json":
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    content = [str(c).lower() for c in d.get("content", [])]
    theme = d.get("theme", {}).get("primary", "?")
    fam = d.get("family", "?")
    score = {k: sum(1 for w in v if w in content) for k, v in HINT.items()}
    rows.append((p.stem, fam, theme, ",".join(content[:8]), score))

print("共 %d 张\n" % len(rows))
for stem, fam, theme, content, score in rows:
    best = sorted(score.items(), key=lambda x: -x[1])
    tag = "/".join("%s:%d" % (k.replace("deco_", ""), v) for k, v in best if v)
    print("%s  [%s/%s]  %s" % (stem, fam, theme, tag))
    print("        content: %s" % content)

print("\n== 按 theme 归堆（可直接进对应概念集的数量）==")
for t in ("ritual", "water", "nature", "court", "ornament"):
    ids = [r[0] for r in rows if r[2] == t]
    print("%-10s %2d 张: %s" % (t, len(ids), " ".join(ids)))
