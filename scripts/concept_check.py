"""概念集校验：python scripts/concept_check.py

逐套检查 data/concept_later/<slug>/ 是否满足 SPEC §7 末与 data/concept_later/README.md：
  1. 三件套齐全（png + txt + json），数量 15–25
  2. caption 首位是概念触发词
  3. caption 不含任何风格锁词（解耦双向要求）
  4. json 合规（必需字段、license 只能是 PD/CC0、theme.primary 在枚举内）
  5. 短边 >= 768（16gb 剖面 §5.2）
  6. 触发词没有泄漏进风格集 caption（data/train/images）

退出码：0 全过 / 1 有 FAIL。
"""
import json
import pathlib
import sys

from PIL import Image

OUT = pathlib.Path("data/concept_later")
TRAIN = pathlib.Path("data/train/images")

SPEC = {
    "ritual": ("deco_ritual", "ritual"),
    "water": ("deco_water", "water"),
    "future_seed": ("deco_future", "machine_or_sky"),
}

STYLE_WORDS = [
    "decomineral style", "flat mineral pigments", "no chiaroscuro",
    "pattern equal to form", "tapestry space", "jewel-like palette",
    "closed color shapes", "ornamental border", "patterned clouds", "gold ground",
]
LICENSES = {"PD", "CC0"}
THEMES = {"ritual", "court", "nature", "water", "ornament", "machine_or_sky"}
REQUIRED = {"id", "style", "theme", "content", "caption_en", "license"}
MIN_SHORT = 768
MIN_N, MAX_N = 15, 25

fails, warns = [], []


def fail(msg):
    fails.append(msg)
    print("  [FAIL] " + msg)


def warn(msg):
    warns.append(msg)
    print("  [WARN] " + msg)


print("== concept_check ==  %s" % OUT)

for slug, (trigger, theme) in SPEC.items():
    d = OUT / slug
    pngs = sorted(d.glob("*.png")) if d.exists() else []
    print("\n-- %s (%s)  %d 张" % (slug, trigger, len(pngs)))

    if not pngs:
        fail("%s 为空" % slug)
        continue
    if len(pngs) < MIN_N:
        fail("%s 只有 %d 张，不足 %d" % (slug, len(pngs), MIN_N))

    for png in pngs:
        stem = png.stem
        txt, js = png.with_suffix(".txt"), png.with_suffix(".json")
        if not txt.exists():
            fail("%s/%s 缺 txt" % (slug, stem))
            continue
        if not js.exists():
            fail("%s/%s 缺 json" % (slug, stem))
            continue

        cap = txt.read_text(encoding="utf-8").strip()
        if not cap:
            fail("%s/%s caption 为空" % (slug, stem))
        elif not cap.lower().startswith(trigger):
            fail("%s/%s caption 未以触发词 %s 开头：%s" % (slug, stem, trigger, cap[:50]))
        lowered = cap.lower()
        for w in STYLE_WORDS:
            if w in lowered:
                fail("%s/%s caption 含风格锁词 '%s'" % (slug, stem, w))

        try:
            md = json.loads(js.read_text(encoding="utf-8"))
        except Exception as e:
            fail("%s/%s json 解析失败 %s" % (slug, stem, e))
            continue
        missing = REQUIRED - set(md)
        if missing:
            fail("%s/%s json 缺字段 %s" % (slug, stem, sorted(missing)))
        if md.get("license") not in LICENSES:
            fail("%s/%s license=%r 不在 PD/CC0" % (slug, stem, md.get("license")))
        if md.get("theme", {}).get("primary") not in THEMES:
            fail("%s/%s theme.primary=%r 不在枚举" % (slug, stem, md.get("theme", {}).get("primary")))
        elif md["theme"]["primary"] != theme:
            warn("%s/%s theme.primary=%s（本套约定 %s）" % (slug, stem, md["theme"]["primary"], theme))
        if md.get("caption_en", "").strip() != cap:
            warn("%s/%s json.caption_en 与 txt 不一致" % (slug, stem))
        if len(md.get("content", [])) < 3:
            warn("%s/%s content 项过少" % (slug, stem))

        try:
            w, h = Image.open(png).size
        except Exception as e:
            fail("%s/%s 打不开 %s" % (slug, stem, e))
            continue
        if min(w, h) < MIN_SHORT:
            fail("%s/%s 短边 %d < %d" % (slug, stem, min(w, h), MIN_SHORT))

    txts = list(d.glob("*.txt"))
    if len(txts) != len(pngs):
        fail("%s txt/png 数量不一致 %d/%d" % (slug, len(txts), len(pngs)))
    if len(pngs) > MAX_N:
        warn("%s 超过 %d 张（建议 15–25）" % (slug, MAX_N))

print("\n== 触发词泄漏检查（风格集 caption 不许出现）==")
leaked = 0
for txt in sorted(TRAIN.glob("*.txt")):
    body = txt.read_text(encoding="utf-8").lower()
    for trigger, _ in SPEC.values():
        if trigger in body:
            fail("风格集 %s 含概念触发词 %s" % (txt.name, trigger))
            leaked += 1
print("  泄漏 %d 处" % leaked)

print("\n" + "-" * 60)
print("结果：FAIL=%d WARN=%d -> %s" % (len(fails), len(warns), "PASS" if not fails else "NO-GO"))
sys.exit(0 if not fails else 1)
