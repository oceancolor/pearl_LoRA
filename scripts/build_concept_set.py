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

Image.MAX_IMAGE_PIXELS = None  # CMA 原图可超 1 亿像素，属可信来源
MAX_LONG = 1600

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
        # 00033 是双语经折装书页：左右各有一栏文字，只留中间画心（裁后 1900x2131）
        "reuse_crop": {"00033": (0.26, 0.02, 0.755, 0.98)},
        # 2026-10-23 用户定的方向：夜林、满月、密叶（参照 data/style_ref/00010、00012）。
        # 用户确认：Gita Govinda 夜林算 ritual；卢梭要。
        "new": [
            {
                "src": "cma_154753",
                "crop": (0.045, 0.07, 0.955, 0.93),  # 去外框花边
                "family": "other_pd",
                "composition": "full_page",
                "content": ["grove", "tree", "krishna", "crown", "woman", "blossom", "stream"],
                "palette": ["malachite", "azurite", "cinnabar", "gold", "jade_white"],
                "caption": 'a dense grove of dark rounded trees and broad leaves, crowned blue-skinned Krishna '
                           'figures hiding among the branches, two women seated on a lawn, sprays of white and '
                           'red blossoms, a grey stream along the bottom',
            },
            {
                "src": "cma_154754",
                "crop": (0.035, 0.06, 0.96, 0.95),
                "family": "other_pd",
                "composition": "full_page",
                "content": ["grove", "tree", "krishna", "flute", "woman", "lotus", "pond"],
                "palette": ["malachite", "azurite", "cinnabar", "ochre", "gold"],
                "caption": 'a grove of dense dark trees under a sky streaked with red cloud bands, a crowned '
                           'blue-skinned Krishna kneeling with a flute, two women seated beneath a leaning tree '
                           'hung with blossom chains, a lotus pond in the foreground',
            },
            {
                "src": "cma_170893",
                "crop": (0.07, 0.07, 0.935, 0.915),
                "family": "other_pd",
                "composition": "full_page",
                "content": ["krishna", "halo", "gopi", "storm_cloud", "tree", "cow", "peacock", "palace"],
                "palette": ["malachite", "azurite", "cinnabar", "ochre", "jade_white"],
                "caption": 'Krishna with a halo standing among women carrying pots under a black sky of rolling '
                           'storm clouds, a dense wall of round green trees, white and brown cows and peacocks '
                           'on a green hill, white palace domes at the left',
            },
            {
                "src": "cma_314235",
                "crop": (0.105, 0.08, 0.895, 0.915),
                "family": "other_pd",
                "composition": "central_figure",
                "content": ["woman", "tree", "night", "hill", "cloud", "bush", "flowering_shrub"],
                "palette": ["malachite", "cinnabar", "ochre", "gold"],
                "caption": 'a lone woman in an orange and gold skirt waiting beneath a tree at night, a dark '
                           'brown hill and a black sky with grey clouds, round green bushes and a flowering '
                           'pink shrub',
            },
            {
                "src": "cma_137824",
                "crop": (0.05, 0.03, 0.955, 0.585),  # 只取上半画面，下方是文字栏
                "family": "persian_miniature",
                "composition": "crop_detail",
                "content": ["forest", "night", "tree", "parrot", "bird", "fox", "nest"],
                "palette": ["azurite", "malachite", "cinnabar", "ochre"],
                "caption": 'a dense forest under a deep blue night sky, a tall tree with pink-tipped leaves full '
                           'of parrots and small birds, a pack of foxes leaping on dark ground',
            },
            {
                "src": "cma_126769",
                "crop": (0.0, 0.0, 1.0, 0.92),  # 去右下角签名
                "family": "other_pd",
                "composition": "full_page",
                "content": ["jungle", "tiger", "buffalo", "banana_leaf", "fruit", "flower", "fern"],
                "palette": ["malachite", "ochre", "cinnabar", "jade_white"],
                "caption": 'a tiger fighting a buffalo deep inside a dense jungle, giant banana leaves and '
                           'hanging pale banana bunches, orange fruits and red flowers, layered fern and grass '
                           'blades filling the whole picture',
            },
            {
                "src": "commons_Henri_Rousseau_known_as_le_Douanier_The_Snake_Charmer_Google",
                "crop": (0.0, 0.0, 1.0, 0.90),  # 去右下角签名「Henri Julien Rousseau 1907」
                "family": "other_pd",
                "composition": "full_page",
                "content": ["full_moon", "jungle", "figure", "flute", "serpent", "wading_bird", "lake"],
                "palette": ["malachite", "ochre", "cinnabar", "jade_white"],
                "caption": 'a dark silhouetted figure playing a flute under a full moon, a black serpent and a '
                           'pink wading bird, dense jungle foliage, tall pale grass and a still lake behind',
            },
            {
                "src": "commons_Henri_Rousseau_The_Equatorial_Jungle_1909_NGA_46688_jpg",
                "crop": (0.0, 0.0, 1.0, 0.89),  # 去右下角签名「Henri Julien Rousseau 1909」
                "family": "other_pd",
                "composition": "full_page",
                "content": ["jungle", "leaf", "lily", "flower", "animal", "grass"],
                "palette": ["malachite", "ochre", "cinnabar", "jade_white"],
                "caption": 'an impenetrable wall of jungle leaves in many greens, pink lilies and a white flower '
                           'spike, a small animal half hidden in the undergrowth, tall pale grass',
            },
            # 2026-10-28 复盘：ritual 前 16 张是「神像+华盖」8 张、夜林 5 张、丛林 3 张三种构图。
            # 补三张不同母题：宫廷集会/行列、单体神猴全身像、夜间园林叙事。
            {
                "src": "cma_162515", "crop": (0.01, 0.02, 0.99, 0.97),
                "family": "other_pd", "composition": "horizontal_register",
                "content": ["assembly", "ruler", "attendant", "elephant", "parasol", "terrace", "carpet", "facade"],
                "palette": ["malachite", "cinnabar", "ochre", "jade_white"],
                "caption": 'a court assembly seen through a two-storey facade, a ruler beneath a parasol on a raised '
                           'terrace, rows of attendants carrying fly-whisks and gifts, an elephant and horses in '
                           'the doorway, a long red carpet on the floor',
            },
            {
                "src": "cma_162460", "crop": (0.02, 0.02, 0.98, 0.943),
                "family": "other_pd", "composition": "central_figure",
                "content": ["monkey_god", "club", "figure", "dhoti", "necklace", "tail"],
                "palette": ["cinnabar", "ochre", "jade_white"],
                "caption": 'a red-bodied monkey god standing with a pale club, tiny figures held in his hand and on '
                           'his shoulder, a yellow cloth at the waist, strings of white beads, a pale plain ground',
            },
            {
                "src": "cma_314412", "crop": (0.05, 0.075, 0.912, 0.902),
                "family": "other_pd", "composition": "full_page",
                "content": ["night", "river", "lying_figure", "woman", "archer", "cart", "tree", "grass"],
                "palette": ["azurite", "malachite", "jade_white", "cinnabar"],
                "caption": 'a pale figure lying on dark ground beside a pale river, three women and a green archer '
                           'standing by, a small red cart and round trees, a black night sky above',
            },
        ],
    },
    "water": {
        "trigger": "deco_water",
        "theme": "water",
        "reuse": ["00022", "00028", "00029", "00030", "00031", "00032", "00045", "00050"],
        # 2026-10-23 用户定：「夜林、满月、密叶」审美 -> 夜色水面。广重版画，裁掉标题框/落款/印章。
        "new": [
            {
                "src": "cma_103358", "crop": (0.03, 0.03, 0.97, 0.92),
                "family": "other_pd", "composition": "full_page",
                "content": ["full_moon", "bay", "island", "pine", "sailboat", "mountain"],
                "palette": ["azurite", "jade_white", "ochre"],
                "caption": 'a full moon over a wide bay, a dark wooded island and chains of small pine islets '
                           'reaching across pale blue water, sailboats far out, mountains on the horizon',
            },
            {
                "src": "cma_106962", "crop": (0.13, 0.07, 0.885, 0.96),
                "family": "other_pd", "composition": "horizontal_register",
                "content": ["full_moon", "bay", "island", "sandbar", "pine", "boat"],
                "palette": ["azurite", "jade_white", "ochre"],
                "caption": 'a wide panorama of a moonlit bay, a small full moon in a hazy sky, dark islands and '
                           'pine-dotted sandbars spread across pale blue water, tiny boats',
            },
            {
                "src": "cma_120225", "crop": (0.17, 0.26, 0.95, 0.96),
                "family": "other_pd", "composition": "full_page",
                "content": ["fireworks", "night_sky", "river", "bridge", "boat", "lantern"],
                "palette": ["azurite", "jade_white", "ochre"],
                "caption": 'fireworks bursting in a dark blue night sky over a broad river, a long wooden bridge '
                           'crowded with figures, many pleasure boats on the water',
            },
            {
                "src": "cma_152490", "crop": (0.21, 0.30, 0.83, 0.96),
                "family": "other_pd", "composition": "full_page",
                "content": ["night_rain", "lake", "pine", "jetty", "boat"],
                "palette": ["azurite", "jade_white", "ochre"],
                "caption": 'night rain falling in long grey lines over a lake, a huge dark pine spreading its '
                           'branches across a stone jetty, deep blue water and a small boat',
            },
            {
                "src": "cma_156858", "crop": (0.31, 0.27, 0.92, 0.945),
                "family": "other_pd", "composition": "crop_detail",
                "content": ["night", "river_mouth", "ship_mast", "ripple", "bridge_pillar"],
                "palette": ["azurite", "jade_white", "cinnabar", "ochre"],
                "caption": 'a night river mouth under a dusky sky, masts of moored ships, dark rippling water and '
                           'a great wooden bridge pillar in the foreground',
            },
            {
                "src": "aic_11054", "crop": (0.035, 0.31, 0.845, 0.945),
                "family": "other_pd", "composition": "crop_detail",
                "content": ["full_moon", "willow", "river", "barge", "boatman", "reed"],
                "palette": ["azurite", "malachite", "jade_white", "ochre"],
                "caption": 'a full moon behind wind-blown willows on a night river, a boatman poling a loaded '
                           'barge through reeds, green banks and pale distant roofs',
            },
            {
                "src": "aic_18366", "crop": (0.08, 0.20, 0.78, 0.95),
                "family": "other_pd", "composition": "crop_detail",
                "content": ["willow", "river", "ferry", "figure", "boat", "bank"],
                "palette": ["azurite", "malachite", "cinnabar", "jade_white"],
                "caption": 'a willow branch hanging over a calm evening river, figures in red at a ferry landing, '
                           'small boats on dark blue water, a wooded far bank',
            },
            # 2026-10-28 机时复盘：water 前 15 张里 7 张是广重同一系列月夜水，8 张复用是琳派浪屏，
            # 出图母题雷同（湖+舟+松+月反复）。补 3 张**不同母题**：骤雨、瀑布、大浪。
            {
                "src": "aic_26545", "crop": (0.018, 0.012, 0.575, 0.545),
                "family": "other_pd", "composition": "full_page",
                "content": ["rain", "river", "raft", "boatman", "far_bank", "tree", "storm_cloud"],
                "palette": ["azurite", "jade_white", "ochre"],
                "caption": 'torrential rain falling in long thin diagonal lines across the whole picture, a low '
                           'raft with a single boatman on a wide grey river, a dark band of trees on the far bank '
                           'under a black storm cloud',
            },
            {
                "src": "cma_95381", "crop": (0.055, 0.175, 0.687, 0.945),
                "family": "other_pd", "composition": "full_page",
                "content": ["waterfall", "cliff", "house", "pine", "figure", "pool", "rock"],
                "palette": ["azurite", "malachite", "cinnabar", "ochre"],
                "caption": 'a tall waterfall dropping in pale blue ribbons down a dark rock face, small houses with '
                           'red roofs and pines below, tiny figures at the pool, orange and blue patterned rock',
            },
            {
                "src": "aic_24645", "crop": (0.155, 0.012, 0.947, 0.962),
                "family": "other_pd", "composition": "full_page",
                "content": ["wave", "foam", "boat", "sea", "mountain", "spray", "claw_foam"],
                "palette": ["azurite", "jade_white", "ochre"],
                "caption": 'a towering wave curling over with claw-like white foam, a deep blue trough below, '
                           'three slender boats riding the swells, a small snow-capped mountain far off',
            },
        ],
    },
    "future_seed": {
        "trigger": "deco_future",
        "theme": "machine_or_sky",
        # 复用：塔楼云 / 神鸟 —— 幻想向，非科幻
        # 00020（屠龙）剔除：波斯书页，画心仅占高度 43%，裁掉上下文字带后短边只剩 555，不达标。
        # 00001（百鸟图）剔除：画内自带两处波斯文小框，裁掉就伤主体；留着会让概念 LoRA 学到文字。
        # 00043（宫台）剔除：实际是带画框翻拍的绿野牧牛图，与 caption 不符，且属翻拍件。
        # 00021（神鸟+骑者）上下各一条文字带，裁画心后约 1170x809。
        "reuse": ["00016", "00021"],
        "reuse_crop": {"00021": (0.065, 0.148, 0.902, 0.632)},
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
            # 2026-10-23 用户定：future 也走「夜林、满月、密叶」审美（幻想，非科幻）
            {
                "src": "commons_Henri_Rousseau_Le_R_ve_Google_Art_Project_jpg",
                "crop": (0.44, 0.0, 1.0, 0.89),  # 去左侧裸体人物与右下签名
                "family": "other_pd",
                "composition": "crop_detail",
                "content": ["full_moon", "jungle", "lotus_flower", "flute_player", "lion", "serpent", "bird"],
                "palette": ["malachite", "azurite", "cinnabar", "ochre", "jade_white"],
                "caption": 'a full moon over a dreamlike jungle, giant flowers in blue and pink, a dark flute '
                           'player in a striped skirt, two lions peering through dense leaves, a coiling orange serpent',
            },
            {
                "src": "commons_La_Boh_mienne_endormie_jpg",
                "crop": (0.0, 0.0, 0.895, 1.0),  # 去右下签名
                "family": "other_pd",
                "composition": "full_page",
                "content": ["full_moon", "night_sky", "lion", "sleeper", "mandolin", "jar", "desert"],
                "palette": ["azurite", "ochre", "cinnabar", "jade_white"],
                "caption": 'a full moon in a deep blue night sky over a desert, a lion sniffing a sleeping wanderer '
                           'in a striped robe, a mandolin and a water jar beside, distant pale mountains',
            },
            {
                "src": "commons_Stories_from_the_Arabian_nights_London_1907_plate_02_jpg",
                "crop": (0.03, 0.02, 0.97, 0.98),
                "family": "other_pd",
                "composition": "central_figure",
                "content": ["genie", "wing", "smoke", "stream", "rock", "fisherman"],
                "palette": ["azurite", "ochre", "cinnabar", "jade_white"],
                "caption": 'a towering winged genie with a jewelled headband rising out of smoke above a rocky '
                           'stream, a tiny fisherman fallen below',
            },
            {
                "src": "cma_314460",
                "crop": (0.05, 0.05, 0.95, 0.95),
                "family": "other_pd",
                "composition": "pattern_field",
                "content": ["vishnu", "serpent", "lotus", "deity", "woman", "cosmic_ocean"],
                "palette": ["cinnabar", "jade_white", "malachite", "ochre", "gold"],
                "caption": 'Vishnu reclining on a white many-headed serpent floating in a sea of lotuses, a '
                           'four-headed god on a lotus above, a woman massaging his feet, rows of pink lotus buds '
                           'and green lotus leaves',
            },
            # 2026-10-28 复盘：future 前 15 张出图母题集中在「寺观正立面 / 单塔」，只两种构图。
            # 补三张**不同母题**：云中坐骑、神兽搏斗、星夜骑队（仍是幻想，非科幻）。
            {
                "src": "cma_130218", "crop": (0.08, 0.045, 0.925, 0.875),
                "family": "other_pd", "composition": "central_figure",
                "content": ["deity", "bull", "cloud", "trident", "woman", "flower", "procession"],
                "palette": ["azurite", "cinnabar", "jade_white", "ochre"],
                "caption": 'a family of pale gods riding a great black bull through a swirl of grey clouds, the '
                           'white-haired god raising a trident, a woman in red beside him, a band of round red and '
                           'yellow flowers below',
            },
            {
                "src": "cma_136475", "crop": (0.03, 0.045, 0.965, 0.915),
                "family": "other_pd", "composition": "horizontal_register",
                "content": ["goddess", "tiger", "demon", "buffalo", "spear", "club", "scroll"],
                "palette": ["cinnabar", "ochre", "jade_white", "malachite"],
                "caption": 'a many-armed goddess riding a white tiger and thrusting a spear at a buffalo demon '
                           'swinging a club, both floating in a flat orange field, red curling scrolls and a green '
                           'ground below',
            },
            {
                "src": "aic_49195", "crop": (0.045, 0.03, 0.955, 0.95),
                "family": "other_pd", "composition": "full_page",
                "content": ["rider", "horse", "parasol", "crowd", "starry_sky", "moon_disc", "horseman"],
                "palette": ["azurite", "cinnabar", "jade_white", "malachite"],
                "caption": 'a rider in yellow on a white horse with an orange parasol overhead, a dense crowd of '
                           'white-robed attendants and horses below, a dark blue sky filled with small pale dots '
                           'and one big round disc',
            },
            {
                # 替换被剔除的 00020（屠龙页）：同样是「神话搏斗」，但无文字栏、尺寸达标
                "src": "cma_130637", "crop": (0.115, 0.16, 0.815, 0.895),
                "family": "other_pd", "composition": "full_page",
                "content": ["archer", "demon", "shield", "sword", "night", "flower_tree", "crown"],
                "palette": ["cinnabar", "malachite", "jade_white", "ochre"],
                "caption": 'a pair of archers with bows drawn against a tall many-headed demon holding a round '
                           'shield and a sword, a red flowering branch at the left, a dark green night field with a '
                           'pale band of clouds along the top',
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
        crop = meta.get("crop")
        if crop:
            # 复用图有时带文字栏（波斯书页、双语经折装），必须裁掉——
            # 风格集就是因为留着文字栏才学出了伪阿拉伯书法（见 CODEBUDDY 2026-10-10 记录）
            im = Image.open(jpeg_or_png).convert("RGB")
            w, h = im.size
            im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
            im.save(dst_png)
        else:
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
        # ★重建前先清掉旧的编号文件：条目数减少时（例如剔除带文字栏的图），
        # 不清理会留下上一轮的 000xx.png，导致张数虚高、编号错位（2026-10-28 踩过）
        if not args.dry_run:
            for old in (OUT / slug).glob("0[0-9][0-9][0-9][0-9].*"):
                old.unlink()
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
            rc = (spec.get("reuse_crop") or {}).get(src_id)
            write_entry(slug, slug, trigger, theme, png, caption,
                        {"idx": idx, "json": meta_json, "crop": rc}, args.dry_run)
            print("  [reuse] %s -> %05d.png %s %s" % (src_id, idx, "[裁切]" if rc else "", caption[:80]))

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
            # 博物馆原图可达 7000–13000px；训练 bucket 上限 1024，存长边 1600 足够且省空间
            if max(im.size) > MAX_LONG:
                im.thumbnail((MAX_LONG, MAX_LONG), Image.LANCZOS)
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
