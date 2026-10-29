# 概念 LoRA 使用手册（2026-10-29 实测）

三支概念 LoRA，**必须与风格 LoRA 叠加使用**，不要单独挂。

## 1. 权重配方（定稿）

| 位置 | 权重 | 说明 |
|---|---|---|
| 风格 `decomineral_v1_16gb.safetensors` | **0.75** | 提供平涂、矿物色、装饰边框。低于 0.7 边框会散 |
| 概念 `deco_ritual` / `deco_water` / `deco_future` | **0.50** | 只负责「画什么」。高于 0.6 会出圈月、边框不齐、色调被训练图带偏 |

叠加方式：kohya 这版不支持逗号传多个 LoRA，先用
`networks/merge_lora.py --models 风格 概念 --ratios 0.75 0.50 --concat` 合成一个，再以 `1.0` 挂上。
`scripts/gen_concept_eval.sh` 已自动处理。

## 2. 已验证能出的母题

| 概念 | 稳定可出 | 弱 |
|---|---|---|
| `deco_ritual` | 莲座神祇 + 华盖 + 成排供养人 + 装饰边框（唐卡式） | — |
| `deco_water` | 月夜海湾与舟、**瀑布**、**大浪**、雨夜松、洲渚 | **暴雨斜线**（写了 torrential rain 也只出平静河面） |
| `deco_future` | 多层塔殿、红墙宫门、云气与星点、成排人物 | 碟状/悬浮造型（见第 4 条） |

## 3. 提示词写法

**构图靠 subject 决定，LoRA 不会自己换构图。** 同一 concept 换 subject 才能换母题，
所以每支建议准备 3–5 条 subject 轮换，不要一个 prompt 出十张。

可直接用的 subject（配合 `SUBJ_OVERRIDE` 或直接写进自己的 prompt）：

- ritual
  - `a ceremony hall in a dense night grove beneath a single full moon, a deity on a lotus throne under a canopy of dark leaves, rows of attendants with banners, a lotus pond`
  - `a court assembly seen through a two-storey facade, a ruler beneath a parasol, attendants with fly-whisks and gifts, an elephant in the doorway`
  - `a red-bodied monkey god standing with a club, strings of beads, a pale plain ground`
- water
  - `a single full moon high in a dark sky over a wide bay, pine-covered islets and small boats`
  - `a tall waterfall dropping in pale ribbons down a dark rock face, houses with red roofs and pines below`
  - `a towering wave curling over with claw-like white foam, slender boats riding the swells`
- future（**不要用 floating**）
  - `a palace gate of red and green masonry among clouds and stars above a dark forest, rows of attendants with banners, towers like sutra pillars`
  - `a nine-storey pagoda among swirling clouds, small figures climbing the terraces`
  - `a walled terrace with gold roofs above a dark pine forest, banners and lanterns`

## 4. 禁用词与负面词

**禁 `floating`**：会直接画出飞碟和碟形悬浮宫殿（2026-10-29 实证）。改用 `among clouds` / `above a forest`。

默认负面词（`gen_concept_eval.sh` 内置）：

```
photograph, realistic lighting, chiaroscuro, 3d render, anime, oil painting,
western perspective, watermark, text, artist name, signature,
two moons, double moon, repeated moons, multiple suns,
ring moon, concentric circles in the sky, donut shape moon
```

- 双月 / 圈月是高频伪影，负面词能压掉，不必为此重训。
- future 建议额外加 `flying machine, ufo, saucer, spacecraft`。

## 5. 不要单独使用概念 LoRA

只挂概念 LoRA（不加风格）时，SDXL 底模的固有陈词会渗进来：棕榈 + 粉月亮 + 帆船、
黄月亮 + 城市天际线——这些母题训练集里根本没有。风格 0.75 能压住。

## 6. 数据边界（写图前先看一眼）

| 概念 | 张数 | 主要来源 |
|---|---|---|
| ritual | 19 | 唐卡/壁画 8、Gita Govinda 夜林 5、卢梭丛林 3、宫廷集会/神猴/夜园 3 |
| water | 18 | 琳派浪屏 8、广重夜水 7、骤雨/瀑布/大浪 3 |
| future | 16 | 波斯恶魔与异兽 6、卢梭幻境 2、杜拉克 1、印度神话 4、塔幢 2、夜战 1 |

所以 ritual 偏「神祇+夜间树林」，water 偏「月下的水」，future 偏「塔殿+云+恶魔」。
超出这个范围的题材，出图会不稳。
