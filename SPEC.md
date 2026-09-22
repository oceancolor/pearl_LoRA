# decomineral

矿物色装饰叙事 · 风格 / 主题解耦数据集与训练规范

版本：1.1  
日期：2026-09-14  
触发词：`decomineral`（人造词，禁止改成画家名、敦煌、九色鹿、明珠）  
目标底模：16GB → FLUX.1-dev LoRA（首选）或 SDXL LoRA；8GB → SDXL LoRA（首选），不默认 FLUX  
授权底线：只收 **PD / CC0**。CC-BY 进复核队列。禁止 NC / ND / 未授权 / 在世作者。

---

## 0. 给后续 Agent 的交接合同

你在 Cursor、CodeBuddy 或 Codex 中接手时，默认遵守下面十条。用户消息里的新指令可以覆盖实现细节，**不能覆盖法律底线**。

1. 这是个人非商用风格 LoRA 项目。先做数据集与标注工具，再做训练配置。不要一上来就训。
2. **禁止**下载、爬取、纳入：在世插画家、上海美影《九色鹿》帧、蔡传隆/林纹《明珠》、数字敦煌 / e-dunhuang / ip.e-dunhuang、Kay Nielsen（卒于 1957，life+70 到 2028）、Eyvind Earle、Errol Le Cain、叶露盈、Victo Ngai、蒋铁峰/丁绍光。
3. **允许**的图像必须在 `provenance.csv` 里有：来源机构、原页 URL、许可、作者卒年或出版年、准入理由。没有 provenance 的文件等于不存在。
4. 风格和主题必须拆开。触发词 `decomineral` 只描述形式语法，不描述佛、凤、龙、飞天、故事。
5. 训练用英文 caption（FLUX/SDXL 更稳）。中文只写在 JSON 的 `notes_zh`，不进 `.txt`。
6. 先实现：目录脚手架、`schema.json`、`provenance.csv` 模板、许可门、裁图清单。再实现博物馆开放 API 下载器。
7. 下载器必须是 **白名单 API / 已知开放接口**（Commons、Met Open Access 等），禁止通用整站爬虫，禁止绕过登录或条款。
8. 硬件剖面只读 `hardware/16gb.yaml` 或 `hardware/8gb.yaml`，不要混用。
9. 不要安装或编写攻击、破解、付费权重盗取。FLUX/SDXL 权重由用户自己按官方许可放置到 `models/`。
10. 用户若要求「再加某某在世画家」，拒绝纳入训练集，改走公共领域近似源。

继承时先读完本文，再读 `data/README.md`（由你生成）。不要依赖聊天记忆。

---

## 1. 项目要什么、不要什么

### 要

用公共领域装饰绘画，抽出一种**可迁移的形式语法**：

- 平涂，不要体积光
- 矿物色：石青、石绿、土红、朱砂、金、玉白
- 纹样 = 形体（羽毛、水、云、山都是织出来的）
- 空间像挂毯 / 壁画 / 细密画，不是透视舞台
- 轮廓清楚，色块闭合

然后用**同一套语法**去生成：宗教仪轨、未来宫殿、水世界。主题靠 caption 与后期概念 LoRA，不靠把主题写进触发词。

### 不要

- 仿某个活着的人
- 把敦煌题材和敦煌语法绑死（否则「未来」「水下」会全部开出莲花）
- 从零训练底模
- 一个文件夹混 15 个画家、一个触发词打天下

---

## 2. 法律准入

### 2.1 硬性允许

同时满足：

| 条件 | 要求 |
|---|---|
| 许可 | `PD` 或 `CC0` |
| 作品本身 | 平面作品：壁画临本页、绢画、插画页、版画、细密画、装饰图案页 |
| 时间 | 作者卒年 ≤ 1955（2026 年按 life+70），**或** 美国出版年 ≤ 1930 |
| 照片权 | 博物馆开放影像明确 CC0/PD；或美国法下公有领域二维作品的忠实复制 |
| 记录 | 写入 provenance，保存 license 快照 URL |

### 2.2 复核队列（默认不训练）

`CC-BY`、`CC-BY-SA`、机构「no known restrictions」但不是 CC0。  
进 `inbox/review/`，人工决定。SA 可能污染衍生模型，默认仍不采用。

### 2.3 一律拒绝

- 数字敦煌、敦煌研究院未书面授权的高清洞壁资源
- 任何 NC、ND、All Rights Reserved
- 在世作者；卒年 1956 及以后
- 动画电影帧、现代绘本扫描、微博/小红书/Pinterest 无许可转存
- 游客自拍、带人物合影的洞窟照片、带色卡/画框/水印/大面积说明牌
- 雕塑、建筑外观、地图、纯书法、照片级文物三维
- Palekh 漆画（多为 20 世纪，仍在版权内）
- 「风格太像但版权不清」的现代临摹

Kay Nielsen 单独禁止，直到 2028-01-01 之后再评估。Edmund Dulac 只收 **1930 年及以前**出版页。

### 2.4 推荐源（白名单）

按开放程度与风格相关度排序。下载器只打这些。

1. **Wikimedia Commons**  
   仅收文件页 license ∈ {PD, CC0}。分类起点（仍须逐文件核许可，分类本身不是许可）：
   - `Category:Mogao Cave paintings`
   - `Category:Cave of the Painters, Kizil`
   - `Category:Ajanta Caves paintings`
   - `Category:Persian miniatures`
   - `Category:Illuminated manuscripts of the Shahnama`
   - `Category:Ivan Bilibin`
   - `Category:Harry Clarke`
   - `Category:Edmund Dulac`（核出版年）
   - `Category:Léon Bakst`
   - `Category:Rimpa school`
   - `Category:Ogata Kōrin`
   - `Category:Tawaraya Sōtatsu`
   - `Category:Henri Rousseau`（只收丛林/平涂装饰感强的，控制在风格集的 8% 以内，防 naive 漂移）
2. **The Met Open Access**（CC0）  
   API：`https://collectionapi.metmuseum.org/public/collection/v1/`  
   检索关键词：`Persian miniature` `Shahnama` `Dunhuang` `Kizil` `Rimpa` `Korin` `Sotatsu` `illuminated manuscript` `Bilibin`（馆藏若有）
3. **Cleveland Museum of Art Open Access**（CC0）
4. **Smithsonian Open Access**（CC0） / **National Museum of Asian Art (Freer/Sackler)**
5. **Rijksmuseum** 开放影像
6. **Getty Open Content**
7. **Library of Congress** 明确 no known restrictions 的插画书页
8. **Internet Archive** 扫描的 1930 及以前插画书（Bilibin 俄童话英译本、Dulac 早期、Clarke 早期）。每页仍要核版权模板。
9. **Gallica (BnF)** Pelliot 相关公开影印：只收标记公有领域的平面页，不收现代摄影集。

**不要写 e-dunhuang 下载器。** 洞窟原作虽古老，研究院数字摄影有自己的条款；本项目用博物馆已开放的平面藏品代替「整壁高清」。

每条 provenance 必须能让人 30 秒点回原页，核到许可。

---

## 3. 风格准入（看图，不看名字）

### 3.1 必须能指出至少 4 条

1. 平涂色块，无明显伦勃朗式光影  
2. 矿物/珐琅/宝石色，不是胶片摄影色  
3. 纹样承担结构：羽、鳞、水、云、叶、地砖是图案  
4. 轮廓或色块边界清楚  
5. 空间是层叠或散点，不是焦点透视舞台  
6. 装饰边框、藻井、地毯、织物可以是画面主体  
7. 人物若存在，也是图案的一部分，不是写实肖像  

### 3.2 风格家族配额（训练前必须满足）

目标入库 **45–70 张**（裁切后的训练图，不是原始下载数）。宁缺毋滥。

| 家族 | 比例 | 作用 |
|---|---|---|
| A 丝路壁画语法（敦煌/克孜尔/阿旃陀的**开放平面图**） | 25–35% | 核心矿物色与平涂 |
| B 波斯 / 印度细密画 | 20–25% | 满铺纹样、宫廷空间、珠宝色 |
| C 俄罗斯童话装饰（Bilibin 等 PD） | 15–20% | 勾线 + 平涂 + 边框，最接近「绘本」 |
| D 彩色玻璃 / 珐琅线（Clarke 等） | 8–12% | 孔雀蓝、闭合色窗 |
| E 琳派金地平面 | 8–12% | 把自然物当纹样 |
| F 纯图案 / 织物 / 藻井局部 | 8–12% | 解开「必须有人物故事」 |
| G 其它 PD 装饰（Bakst 舞台、早期 Dulac） | ≤8% | 防止过拟合某一窟 |

同一面墙、同一页书最多 **3 张裁切** 进训练集，避免过拟合一块斑驳。

### 3.3 主题配额（这是解耦的关键）

若宗教内容超过 45%，「未来 / 水世界」会塌。强制内容标签分布：

| `theme.primary` | 最少张数 | 例子 |
|---|---|---|
| `ritual` | 8 | 供养、仪仗、圣树、藻井、神像 **但不写进触发词** |
| `court` | 8 | 宫殿、城郭、仪仗、织物、宝座 |
| `nature` | 8 | 树石、鸟、花、山，全是纹样化的 |
| `water` | 8 | 河、池、船、鱼、浪纹、水下宫（细密画里很多） |
| `ornament` | 6 | 几乎无情节的图案局部 |
| `machine_or_sky` | 4 | 尽量找：天文仪、战船、飞车、星象、火箭式云车、机关鸟。PD 里少，缺则保持为 4，**禁止用现代科幻插画补** |

`future` 不是训练集主题。训练集只提供「非宗教的建筑 / 器物 / 天空机械苗头」。未来感靠生成期提示词去翻译。

---

## 4. 仓库目录（Agent 按此创建）

```text
decomineral/
  SPEC.md                          # 本文件副本
  README.md
  schema/caption.schema.json
  hardware/16gb.yaml
  hardware/8gb.yaml
  prompts/generate_en.yaml         # 生成期提示词合同
  data/
    README.md
    provenance.csv
    inbox/raw/                     # 原下，永不直接训练
    inbox/review/                  # CC-BY 等
    rejected/                      # 留下拒绝理由
    crops/                         # 人工或半自动裁切
    train/
      images/                      # 最终训练图，与 txt 同名
      captions/                    # 可选，若 caption 不放在 images 旁
    concept_later/
      ritual/
      water/
      future_seed/
  scripts/
    init_tree.py
    fetch_met.py
    fetch_commons.py
    license_gate.py
    caption_lint.py
    make_kohya_structure.py
  models/                          # gitignore，用户自备权重
  output/lora/
  logs/
```

`provenance.csv` 列：

```text
file_id,orig_filename,train_filename,source,institution,page_url,direct_url,license,license_url,creator,creator_death_year,publication_year,family,theme_primary,width,height,sha256,decision,decision_reason,downloaded_at
```

`decision` ∈ `train | review | reject`。

---

## 5. 采集与预处理

### 5.1 下载

- 一张原图一个 `file_id`（ULID 或 `src_accession`）。
- 保存原文件 + 原页 HTML/JSON 许可片段到 `inbox/raw/<file_id>/`。
- 计算 sha256。重复像素或重复 sha 丢弃。
- User-Agent 写清楚项目名与联系方式；遵守 Commons 与 Met 的速率。Met 约 80 req/s 上限，实际用 1–2 req/s。

### 5.2 图像质量门

拒绝：

- 短边 < 768（8GB 剖面可放到 640，但不得低于 640）
- JPEG 块效应严重、屏幕翻拍、书脊扭曲
- 大面积斑驳到纹样不可读
- 现代修复成油画味
- 水印、印刷网纹压过线条
- 与风格清单匹配项 < 4

### 5.3 裁切

- 去边框外的博物馆壁、色卡、图注。
- 允许 1 张全图构图 + 1–2 张「语法特写」（藻井、水纹、羽纹、宫殿立面）。
- 特写必须仍是完整装饰语言，不要无意义墙皮。
- 不在训练图上写字、不叠触发词水印。
- 输出 RGB PNG 或高质量 JPEG q≥92。
- 目标边：16GB 短边 ≥ 1024；8GB 短边 ≥ 768。不要强行拉伸，用 bucketing。

### 5.4 不要做的增强

- 禁止风格迁移、AI 放大当训练图（Real-ESRGAN 仅当原图已过门且只做轻度锐化时，须在 provenance 标注 `upscaled=1`，且这类图 ≤ 10%）。
- 禁止把彩色玻璃照片 HDR 化。
- 禁止自动配色「更敦煌」。

---

## 6. 标注格式（风格与主题拆开）

每张训练图三件套：

- `train/images/00023.png`
- `train/images/00023.txt`  英文训练 caption
- `train/images/00023.json` 机器可检的完整标注

### 6.1 JSON schema（Agent 写成 `schema/caption.schema.json`）

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "decomineral caption",
  "type": "object",
  "required": ["id", "style", "theme", "content", "caption_en", "license"],
  "properties": {
    "id": { "type": "string" },
    "license": { "enum": ["PD", "CC0"] },
    "family": {
      "enum": ["silkroad_mural", "persian_miniature", "bilibin", "clarkestain", "rimpa", "pure_ornament", "other_pd"]
    },
    "style": {
      "type": "object",
      "required": ["traits"],
      "properties": {
        "traits": {
          "type": "array",
          "minItems": 4,
          "items": {
            "enum": [
              "flat_fill",
              "mineral_pigment",
              "pattern_equals_form",
              "no_chiaroscuro",
              "closed_outline",
              "ornamental_border",
              "tapestry_space",
              "gold_ground",
              "enamel_cells",
              "jewel_palette",
              "patterned_terrain",
              "radial_gradient",
              "nonfocal_figures"
            ]
          }
        },
        "palette": {
          "type": "array",
          "items": {
            "enum": ["azurite", "malachite", "cinnabar", "ochre", "gold", "jade_white", "lapis", "soot", "coral", "turquoise"]
          }
        }
      }
    },
    "theme": {
      "type": "object",
      "required": ["primary"],
      "properties": {
        "primary": {
          "enum": ["ritual", "court", "nature", "water", "ornament", "machine_or_sky"]
        },
        "secondary": { "type": "array", "items": { "type": "string" } }
      }
    },
    "content": {
      "type": "array",
      "items": { "type": "string" },
      "description": "nouns only: boat, wave-pattern, palace, bird, tree, throne. No artist names. No 'dunhuang style'."
    },
    "composition": {
      "enum": ["full_page", "border_frame", "horizontal_register", "central_figure", "pattern_field", "crop_detail"]
    },
    "caption_en": { "type": "string", "minLength": 40, "maxLength": 600 },
    "notes_zh": { "type": "string" },
    "split": { "enum": ["train", "val"] }
  }
}
```

val 留 4–6 张，覆盖不同 family 与 theme，不参与训练，只作抽检对照。

### 6.2 英文 caption 合同

固定顺序，四段，用逗号连接：

```text
decomineral style, <FORM GRAMMAR>, <SUBJECT NOUNS>, <PALETTE AND MEDIUM>
```

规则：

1. **永远**以 `decomineral style` 开头（小写）。
2. FORM GRAMMAR 只准用下面词汇的子集：  
   `flat mineral pigments` `no chiaroscuro` `pattern equal to form` `closed color shapes` `ornamental border` `tapestry space` `gold ground` `enamel cell outlines` `jewel-like palette` `woven feathers` `patterned water` `patterned clouds` `geometric pavement` `mountains patterned as dense forest` `color radiating outward from the center` `figures in large non-focal areas`
3. SUBJECT 用普通名词讲画面里有什么。可以出现 `Buddha` `angel` `phoenix` `dragon` `boat` `palace` `waves`——因为那是内容。  
   **禁止**：`Dunhuang style` `in the style of Bilibin` `Kay Nielsen` `Chinese animation` `nine-color deer` `Victo Ngai`。
4. 画家名、博物馆名、洞窟号不准进 `.txt`。只进 JSON / provenance。
5. FLUX 用完整短语，不要 tag 堆砌超过 1 行垃圾词。
6. 同一张图不要又写 `Buddhist mural` 又写 `decomineral` 当同义词。宗教信息放在 SUBJECT 段。

**好例子**

```text
decomineral style, flat mineral pigments, no chiaroscuro, pattern equal to form, tapestry space, ornamental border, a palace beside patterned water with two boats and fish-scale waves, malachite green, azurite blue, gold
```

```text
decomineral style, flat mineral pigments, closed color shapes, jewel-like palette, enamel cell outlines, a seated ritual figure under a patterned canopy with attendants, cinnabar, lapis, gold, jade white
```

```text
decomineral style, gold ground, pattern equal to form, a pair of cranes and flowing water treated as fabric design, malachite, coral, gold
```

**坏例子**

```text
decomineral, dunhuang, nine color deer, beautiful, 8k, masterpiece, in the style of cai chuanlong
```

```text
a painting of the Mogao caves, Dunhuang style mural
```

后者把地点风格绑死，解耦失败。

### 6.3 lint 必须拦截

`scripts/caption_lint.py` 对每条 `.txt` 检查：

- 开头是 `decomineral style`
- 不含黑名单词表：`dunhuang style`, `mogao style`, `bilibin style`, `nielsen`, `ngai`, `ye luying`, `earle`, `le cain`, `nine-color`, `jiu se lu`, `ming zhu`, `anime`, `photoreal`, `8k`, `masterpiece`
- 至少 1 个 form grammar 短语
- 至少 1 个 content 名词
- JSON `theme.primary` 与 caption 大意不冲突（water 图必须出现 water/wave/boat/fish/lotus-pond 等之一）
- 统计 theme 分布，不满足第 3.3 节配额则失败退出

---

## 7. 生成期提示词合同（训练之后）

文件：`prompts/generate_en.yaml`

风格锁永远同一句，主题只改 SUBJECT。

```yaml
style_lock: >-
  decomineral style, flat mineral pigments, no chiaroscuro,
  pattern equal to form, tapestry space, jewel-like palette,
  closed color shapes, ornamental border

negative: >-
  photograph, realistic lighting, chiaroscuro, 3d render, anime,
  oil painting, western perspective, watermark, text, artist name

branches:
  ritual:
    subject: >-
      a ceremonial hall with canopy, attendants, sacred tree and
      geometric pavement, ritual but not a copy of a known cave
  future:
    subject: >-
      an orbital palace and procession of machine-bodied attendants,
      towers like sutra pillars, sky-boats treated as ornament not sci-fi chrome
  water:
    subject: >-
      an underwater palace, fish-scale waves, lotus as fabric, boats
      and palaces stacked like a tapestry
```

拼法：

```text
<lora:decomineral:0.8>, {style_lock}, {subject}, malachite, azurite, cinnabar, gold
```

若 `future` 仍长出飞天与莲，说明训练集 ritual 过重，应补 `court` / `machine_or_sky` / `water`，而不是提高权重、也不是去爬在世科幻画家。

概念 LoRA 只在风格 LoRA 稳定后做，每支 15–25 张，触发词另起：`deco_ritual` `deco_water` `deco_future`。永远不要把概念触发词写进风格集 caption。

---

## 8. 硬件剖面

Agent 生成这两个 YAML，训练脚本只引用其中一个。

### 8.1 `hardware/16gb.yaml`（RTX 5060 Ti 16GB 等）

```yaml
profile: 16gb
preferred_base: flux1-dev          # 用户自备，遵守 FLUX 非商用条款
fallback_base: sdxl
lora:
  rank: 16
  alpha: 16
  blocks: default_for_flux_or_sdxl
train:
  resolution_buckets: [768, 896, 1024]
  batch_size: 1
  grad_accum: 4
  optimizer: adamw8bit
  lr: 1.0e-4
  lr_scheduler: cosine
  warmup_steps: 50
  max_train_steps: 2000            # 约 45–60 张时；按 30 张可 1500，70 张可 2500
  mixed_precision: bf16            # 不支持则 fp16
  gradient_checkpointing: true
  cache_latents: true
repeats_formula: "target_steps / (image_count * epochs) ; epochs=1–2"
time_budget_hours: 1.5
oom_fallback:
  - rank: 8
  - resolution_max: 896
  - cache_latents: false
notes:
  - 不要 full finetune
  - 不要把 text encoder 学太狠；FLUX 只训 LoRA
  - 每 250 step 出 4 张固定 prompt 抽检：ritual / court / water / future
```

### 8.2 `hardware/8gb.yaml`

```yaml
profile: 8gb
preferred_base: sdxl
disallow_default: flux1-dev        # 除非用户明确要 block-swap 且接受 3h+/轮
lora:
  rank: 8
  alpha: 8
train:
  resolution_buckets: [640, 768, 832]
  batch_size: 1
  grad_accum: 8
  optimizer: adamw8bit
  lr: 8.0e-5
  max_train_steps: 1800
  mixed_precision: fp16
  gradient_checkpointing: true
  cache_latents: true
  vae_slicing: true
time_budget_hours: 3
oom_fallback:
  - resolution_max: 704
  - rank: 4
  - 改 SD 1.5 仅作最后手段，需另写 caption 更短
notes:
  - 8GB 不要并行下载+训练
  - 训练图短边 768 即可，不要迷信 1024
```

抽检 4 条固定 prompt 必须写入 `prompts/eval_grid.txt`，两台机器用同一随机种子对照。

---

## 9. 最小实验（先做这个才允许加数据）

1. 过许可门的图 ≥ 36 张，theme 配额达标。  
2. lint 通过。  
3. 按本机剖面训 1 轮。  
4. 固定 4 条 branch prompt 各出 8 张。  
5. 人工用下面的及格线打分。

及格：

- 一眼平涂，不是照片或厚涂油画
- 三张 branch 能看出同一家族（矿物色 + 纹样空间）
- `future` 允许古怪，但不许只有飞天换铁盔
- 没有画家签名、没有洞窟编号、没有训练水印

不及格就改数据，不改触发词、不加在世作者。

---

## 10. Agent 应落地的脚本顺序

按这个 PR 顺序做，每个 PR 可独立运行。

| 顺序 | 产出 | 完成定义 |
|---|---|---|
| 1 | `init_tree.py` + 空 csv + 两个 yaml + schema | 目录可建、schema 可校验 |
| 2 | `license_gate.py` | 读 Commons/Met 元数据 JSON，非 PD/CC0 拒写 train |
| 3 | `fetch_met.py` | 用 Open Access API 按关键词拉候选，不自动当 train |
| 4 | `fetch_commons.py` | 逐文件核 license 模板，保存 file page url |
| 5 | `caption_lint.py` | 见 6.3 |
| 6 | `make_kohya_structure.py` | 按 16g/8g 生成训练命令，不下载盗版权重 |
| 7 | 人工裁切辅助：打网格、去边；自动裁只做建议 | 最终裁切必须能人工过目 |

不要在第 1–2 步完成前写训练启动器。

伪接口约定：

```text
python scripts/fetch_met.py --query "Shahnama miniature" --out data/inbox/raw
python scripts/license_gate.py --inbox data/inbox/raw --csv data/provenance.csv
python scripts/caption_lint.py --train data/train/images
```

---

## 11. 已知陷阱

- Commons 分类里混有现代游客摄影，许可是自己的，不是壁画的。必须读文件页。
- 「北魏壁画」现代临摹可能有临摹者版权。只收明确 PD 的历史平面复制。
- Bilibin 有大量现代翻绘。只收 1910s 前后印刷页。
- Rousseau 会把模型拉向素人丛林，限 8%。
- 用中文 caption 训 FLUX，风格锁会不稳。
- 一张图 caption 里写了画家名，LoRA 会学成「签名器」。
- 主题解耦失败的第一反应永远是：查 `theme.primary` 直方图，不是加 GPU。

---

## 12. 给用户的使用方式

把本文件放进新仓库根目录，命名为 `SPEC.md`。在 Cursor / Codex 里只发：

```text
Read SPEC.md. Execute section 10 in order. Hardware profile: 16gb.
Do not scrape anything outside the source allowlist. Do not add living artists.
```

8GB 把 `16gb` 改成 `8gb`。

权重、训练框架（ai-toolkit / sd-scripts / SimpleTuner）由当时环境决定，但 rank、分辨率、步数、caption 合同以本文第 6–8 节为准。

---

## 13. 变更记录

- **1.0**（2026-09-09）：初版。
- **1.1**（2026-09-14）：扩展风格语法（§6.1 `style.traits` 与 §6.2 FORM GRAMMAR 同步）：新增装饰画传统技法词条 `patterned_terrain`（山体满铺纹理、读来如长满树林）、`radial_gradient`（自中心向外轮环式渐变）、`nonfocal_figures`（人物置于非焦点的大面积区域以制造压迫感/冲突）。配色仍用 §6.1 `palette` 矿物色枚举（石青/石绿/朱砂/金/土红/玉白等），无需像素级色彩统计。以上均为**公共领域装饰画传统的方法总结**，不含任何受版权保护的作品、图像或像素衍生数据；训练图仍 100% 来自 PD/CC0。
