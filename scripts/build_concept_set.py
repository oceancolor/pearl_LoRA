"""构建概念 LoRA 数据集：data/concept_later/{ritual,water,future_seed}/

两类来源：
  1. reuse —— 复用风格集图（同一张图可服务两个 LoRA），caption 去掉风格锁词、换成概念触发词
  2. new   —— 新图，按给定裁切框去掉文字栏后落盘

硬规则（SPEC §7 末 + data/concept_later/README.md）：
  - 概念触发词必须在 caption 首位
  - 概念集 caption 不写任何风格锁词（风格由风格 LoRA 负责，解耦是双向的）

用法：python scripts/build_concept_set.py            # 正式生成
      python scripts/build_concept_set.py --dry-run  # 只打印，不写盘
"""
import argparse
import json
import pathlib
import re
import shutil

from PIL import Image

TRAIN = pathlib.Path("data/train/images")
RAW = pathlib.Path("data/inbox/raw")
OUT = pathlib.Path("data/concept_later")

# 风格锁词：概念集 caption 里一个都不许留
STYLE_DROP = {
    "decomineral style", "flat mineral pigments", "no chiaroscuro",
    "pattern equal to form", "tapestry space", "jewel-like palette",
    "closed color shapes", "ornamental border", "patterned clouds",
    "gold ground",  # 地色属风格属性（gold_ground trait），不由概念 LoRA 承担
}

TRAITS_BASE = ["flat_fill", "mineral_pigment", "no_chiaroscuro", "closed_outline"]

CONCEPTS = {
    "ritual": {
        "trigger": "deco_ritual",
        "theme": "ritual",
        "reuse": ["00007", "00008", "00009", "00033", "00034", "00035", "00042", "00049"],
        "new": [],
    },
    "water": {
        "trigger": "deco_water",
        "theme": "water",
        "reuse": ["00022", "00028", "00029", "00030", "00031", "00032", "00045", "00050"],
        "new": [],
    },
    "future_seed": {
        "trigger": "deco_future",
        "theme": "machine_or_sky",
        # 复用：塔楼云 / 屠龙 / 神鸟 / 群鸟 / 宫台 —— 幻想向，非科幻
        "reuse": ["00016", "00020", "00021", "00001", "00043"],
        "new": [
            {
                "src": "commons_The_Tortoise_Folio_from_an_Aja_ib_al_Makhluqat_Wonders_of_C",
                "crop": (0.04, 0.03, 0.96, 0.925),  # 目检：底部有一行题记，向上收
                "family": "other_pd",
                "composition": "full_page",
                "content": ["tortoise", "creature", "cloud", "serpent", "fish", "scaled_ground"],
                "palette": ["cinnabar", "ochre", "azurite", "jade_white"],
                "caption": 'a giant tortoise with a patterned shell among red swirling clouds, '
                           'a reclining figure and a serpent beside it, fish and scaled ground below',
            },
            {
                "src": "commons_An_Illustrated_Leaf_from_the_Shah_Isma_il_II_Manuscript_of_F",
                "crop": (0.205, 0.16, 0.785, 0.555),  # 目检4：顶部一行 + 底部一行小字
                "family": "persian_miniature",
                "composition": "crop_detail",
                "content": ["cloud", "rider", "horse", "tower", "roof", "garden"],
                "palette": ["azurite", "cinnabar", "malachite", "gold"],
                "caption": 'a rider on a horse before a walled pavilion, heavy blue clouds filling the sky, '
                           'red roofs and a garden terrace above',
            },
            {
                "src": "commons_Shahnameh_The_Div_Akvan_throws_Rustam_into_the_sea_jpg",
                "crop": (0.12, 0.40, 0.945, 0.80),  # 目检4：顶部右侧仍有一行
                "family": "persian_miniature",
                "composition": "central_figure",
                "content": ["div", "horned_figure", "boulder", "cloud", "mountain", "tree"],
                "palette": ["azurite", "jade_white", "cinnabar", "ochre", "malachite"],
                "caption": 'a horned div lifting a slab of rock overhead, islands of cloud ringing the sky, '
                           'jagged mountains and flowering trees below',
            },
            {
                "src": "commons_Kay_Ka_us_chained_in_a_grotto_by_the_white_demon_FGA_F2006_7",
                "crop": (0.02, 0.40, 0.98, 0.78),  # 目检4：字行更靠上（0.787）
                "family": "persian_miniature",
                "composition": "crop_detail",
                "content": ["demon", "grotto", "rock", "king", "attendant", "banner"],
                "palette": ["azurite", "cinnabar", "ochre", "jade_white"],
                "caption": 'a white demon seated in a dark grotto of violet rocks, a bound king and attendants '
                           'among jutting stone shelves, small trees along the ledges',
            },
            {
                "src": "commons_An_illustrated_leaf_from_a_manuscript_of_Firdausi_s_Shahname",
                "crop": (0.055, 0.275, 0.945, 0.875),
                "family": "persian_miniature",
                "composition": "central_figure",
                "content": ["div", "demon", "boulder", "cave", "beast", "gold_ground"],
                "palette": ["cinnabar", "azurite", "malachite", "gold", "ochre"],
                "caption": 'a ring of coloured divs raising boulders on a golden ground, a combat in a black cave mouth, '
                           'horned and blue-skinned figures crowding the rocks',
            },
            {
                "src": "commons_Seventh_Labour_of_Rostam_Killing_the_White_Demon_jpg",
                "crop": (0.08, 0.38, 0.92, 0.85),  # 目检4：顶部右侧仍有一行
                "family": "persian_miniature",
                "composition": "crop_detail",
                "content": ["white_demon", "cave", "mountain", "tree", "warrior", "flame"],
                "palette": ["azurite", "cinnabar", "ochre", "malachite", "gold"],
                "caption": 'a white demon wrestling a warrior inside a black cave mouth, orange and blue '
                           'mountains of patterned rock, cypress trees and a watching figure above',
            },
        ],
    },
}


def strip_style(caption):
    parts = [p.strip() for p in caption.split(",")]
    kept = [p for p in parts if p and p.lower() not in STYLE_DROP]
    out = ", ".join(kept)
    # 描述句内部的「on a gold ground」同样属风格（gold_ground trait），一并抹掉
    return re.sub(r"\s*on (a )?gold ground", "", out, flags=re.I)


def write_entry(concept, slug, trigger, theme, jpeg_or_png, caption, meta, dry):
    dst_png = OUT / slug / ("%05d.png" % meta["idx"])
    dst_txt = dst_png.with_suffix(".txt")
    dst_json = dst_png.with_suffix(".json")
    if not dry:
        shutil.copyfile(jpeg_or_png, dst_png)
        dst_txt.write_text(caption, encoding="utf-8")
        dst_json.write_text(json.dumps(meta["json"], ensure_ascii=False, indent=2), encoding="utf-8")
    return dst_png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for slug, spec in CONCEPTS.items():
        trigger, theme = spec["trigger"], spec["theme"]
        (OUT / slug).mkdir(parents=True, exist_ok=True)
        idx = 0
        print("\n== %s (%s) ==" % (slug, trigger))

        for src_id in spec["reuse"]:
            png = TRAIN / (src_id + ".png")
            js = json.loads((TRAIN / (src_id + ".json")).read_text(encoding="utf-8"))
            if not png.exists():
                print("  MISSING %s" % src_id)
                continue
            body = strip_style(js.get("caption_en", ""))
            caption = "%s, %s" % (trigger, body)
            idx += 1
            meta_json = {
                "id": "%s_%05d" % (slug, idx),
                "license": js.get("license", "PD"),
                "family": js.get("family", "other_pd"),
                "style": {"traits": js.get("style", {}).get("traits", TRAITS_BASE),
                          "palette": js.get("style", {}).get("palette", [])},
                "theme": {"primary": theme, "secondary": js.get("theme", {}).get("secondary", [])},
                "content": js.get("content", []),
                "composition": js.get("composition", "central_figure"),
                "caption_en": caption,
                "notes_zh": "复用风格集 %s；caption 已去风格锁词、加概念触发词 %s。" % (src_id, trigger),
                "split": "train",
                "concept": slug,
                "reused_from": src_id,
            }
            write_entry(slug, slug, trigger, theme, png, caption, {"idx": idx, "json": meta_json}, args.dry_run)
            print("  [reuse] %s -> %05d.png  %s" % (src_id, idx, caption[:88]))

        for item in spec["new"]:
            d = RAW / item["src"]
            src = next((p for n in ("image.jpg", "image.jpeg", "image.png", "image.webp")
                        if (p := d / n).exists()), None)
            if not src:
                print("  MISSING %s" % item["src"])
                continue
            mj = json.loads((d / "meta.json").read_text(encoding="utf-8")) if (d / "meta.json").exists() else {}
            im = Image.open(src).convert("RGB")
            w, h = im.size
            crop = item.get("crop")
            if crop:
                l, t, r, b = crop
                box = (int(l * w), int(t * h), int(r * w), int(b * h))
                im = im.crop(box)
            cw, ch = im.size
            short = min(cw, ch)
            flag = "OK" if short >= 768 else "SMALL(<768) 不可用"
            caption = "%s, %s" % (trigger, item["caption"])
            idx += 1
            tmp = OUT / slug / (".tmp_%05d.png" % idx)
            if not args.dry_run:
                im.save(tmp)
            meta_json = {
                "id": "%s_%05d" % (slug, idx),
                "license": mj.get("license", "CC0"),
                "family": item.get("family", "other_pd"),
                "style": {"traits": TRAITS_BASE, "palette": item["palette"]},
                "theme": {"primary": theme, "secondary": ["creature"] if slug == "future_seed" else []},
                "content": item["content"],
                "composition": item.get("composition", "crop_detail"),
                "caption_en": caption,
                "notes_zh": "新补。来源 %s（%s，%s）。裁切 %s。" % (
                    mj.get("page_url", ""), mj.get("institution", ""), mj.get("publication_year", ""), crop),
                "split": "train",
                "concept": slug,
                "source_file_id": item["src"],
                "source_sha256": mj.get("sha256", ""),
            }
            if not args.dry_run:
                tmp.replace(OUT / slug / ("%05d.png" % idx))
                (OUT / slug / ("%05d.txt" % idx)).write_text(caption, encoding="utf-8")
                (OUT / slug / ("%05d.json" % idx)).write_text(
                    json.dumps(meta_json, ensure_ascii=False, indent=2), encoding="utf-8")
            print("  [new  ] %s -> %05d.png  %dx%d short=%d %s" % (item["src"][:46], idx, cw, ch, short, flag))
            print("          %s" % caption[:88])

        print("  合计 %d 张（目标 15–25）%s" % (idx, "" if idx >= 15 else "  ** 缺口 %d **" % (15 - idx)))


if __name__ == "__main__":
    main()
