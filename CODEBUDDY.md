# CODEBUDDY.md This file provides guidance to CodeBuddy when working with code in this repository.

## 仓库现状（更新于 2026-09-17，数据集阶段完成）

- 已按 SPEC §4 建好目录骨架（`schema/ hardware/ prompts/ data/{inbox/raw, inbox/review, rejected, crops, train/images, train/captions, concept_later} scripts/ models/ output/lora/ logs/`，空目录有 `.gitkeep`），并生成根 `SPEC.md`（经哈希校验与 docs 源逐字一致）、`data/README.md`、`schema/caption.schema.json`、`hardware/{8gb,16gb}.yaml`、`prompts/generate_en.yaml`、`data/provenance.csv`（表头）、`.gitignore`。
- **已实现脚本**：`init_tree.py`、`env_check.py`、`license_gate.py`、`caption_lint.py`、`make_kohya_structure.py`、`fetch_met.py`、`fetch_commons.py`、`crop_assist.py`（§10 第 7 步，自动去边**仅作建议**，产出 `data/crops/<file_id>.png` + `_proposals.json`，须人工确认）、`_recover_fill.py`（崩溃恢复用，幂等回填 `provenance.csv` 的 `train_filename`，并按三件套 json 校正 `family`/`theme_primary`）。**已完成 `prompts/eval_grid.txt`**（4 条固定抽检：ritual/court/water/future + negative + seed 20260915）。`court` 分支 subject 此前 SPEC §7 未给，由用户 2026-09-17 依 §3.3「宫殿、城郭、仪仗、织物、宝座」口述补写，已同步进 `prompts/generate_en.yaml`。**SPEC §10 落地项现已全数完成，只剩正式训练执行（等 GPU 机）。**
- **已生成 `configs/`**：`dataset_8gb.toml`（bucket 640–832、caption 不打乱、禁色彩/镜像增强）+ `sdxl_lora_8gb.toml`（rank/alpha 8、AdamW8bit、fp16、1800 步、seed 20260915）。数值全部镜像 `hardware/8gb.yaml`，**改一处必须同步另一处**；`make_kohya_structure.py` 打印的老命令行里残留 `--min_silo_noise_offset` 是错误参数名（configs 里已改为 `min_snr_gamma=5` / `noise_offset=0.0`），以 toml 为准。
- `provenance.csv` 现 **144 行（train=50 / review=38 / reject=56）**。已实跑 `fetch_met.py` / `fetch_commons.py` 十几轮。已实跑 `fetch_met.py` / `fetch_commons.py` 十几轮。**★关键教训（检索侧）**：Met 的 `search?q=` 接口已退化——多数查询返回同一组默认结果（Stela 544320 / Bust 200668 / 圣杰罗姆 437261 / Marie-Antoinette 824771…），`q=*` 全库只返回 178 条，按部门限定也只有 3–7 条 → **Met 侧发现能力已枯竭**，只适合用 `_probe_met.py --ids` 按已知 objectID 精取。Commons 侧改为 `--search`（全文检索，绕过分类只给字母序前 N 条的问题），是 2026-09-16 之后的主力；但 Commons 会 403 限流（退避 30–60s + delay 4s）。
- **`data/train/images/` 现有 38 张三件套（00001、00006–00010、00012–00014、00016–00024、00027–00043、00045–00049；编号有缺口属正常，见下）**，`data/val/` 5 张（00006/00011/00015/00023/00044，`split=val`，涵盖 A/ritual、B/court、B/water、E/nature、F/ornament）。**theme 配额已达标**：ritual 8 / court 8 / nature 8 / water 8 / ornament 6；`machine_or_sky` 0（SPEC §3.3 明写「PD 里少，缺则保持 4」，属**软配额**）。家族分布：B 波斯 17 / A 丝路 8 / F 纯图案 6 / E 琳派 6 / G 其它 1（C 俄童话已归零，见下）。
- **三道门现已无条件全绿**（不加任何降级参数）：`license_gate --csv` EXIT=0 → `caption_lint --train data/train/images` **PASS（LINT=0，0 问题）** → `make_kohya_structure.py --profile 8gb` EXIT=0（`metadata.json` 38 条）。正式训练命令落 `logs/smoke_train_cmd.txt`（冒烟 10 步），正式档走 `configs/*.toml`。
- `data/crops/_hold/` 暂存 **8 张待定三件套**（有 caption/json，只差一个条件即可归位）：00003/00004/00005 = Bilibin 插图，**短边 638/621/564 < 640 且 Commons 无更大版本**；00025/00026 = IMJ Shahnameh 插图，**Commons 只给上传日期 2018、无作品年代证据（§2.1）**；00024 = Brooklyn《Khusraw 发现 Shirin 沐浴》，**原图仅 768x760，达不到 16gb 的 768 门槛**。原因均写进 provenance 的 decision_reason。
- **§3.3 配额下限 = 38 张 train**（8+8+8+8+6）。切 val 后 train 必须 ≥38 才不破坏配额，所以**补图与切 val 要一起算**：38 train + 5 val = 43 张总量。
- **标注坑（已踩过）**：`geometric pavement` 是 §6.2 的 **caption 短语**，**不是** §6.1 的 `style.traits` 键（SPEC traits 枚举只有 13 个）；把它写进 json 会 schema 校验失败。同理 `woven feathers` / `patterned water` / `patterned clouds` 也只准进 caption，不准进 traits。
- **§6.3 第 5 条是硬校验**：`theme.primary` 与 caption 大意必须一致，靠 `THEME_HINTS` 关键词匹配（如 ritual 须含 canopy/attendant/sacred/throne/seated 之一，water 须含 water/wave/boat/fish/lotus 之一）。写了「heavenly king」但没写 sacred/throne 会被判冲突 → 加词即可。
- **`caption_lint.py` 有硬/软配额之分（2026-09-17 改）**：`THEME_MIN` 之外新增 `THEME_SOFT = {"machine_or_sky"}`。依据 SPEC §3.3「尽量找，PD 里少，缺则保持 4，禁止用现代科幻插画补」——缺它只 WARN 不 FAIL，其余主题是硬配额。改造前它把 machine_or_sky 当硬指标，导致数据集明明达标却无法 PASS。
- **`_triage.py` 的字段写回列表**：支持 `decision / family / theme_primary / train_filename / creator / creator_death_year / publication_year` + `reason`→`decision_reason`。**给新条目加字段时必须同步这个元组**，否则字段不落盘（2026-09-16 因缺 `creator_death_year` 白给过卒年证据仍过不了门）。补丁要写在 `if k in t:` 保护**之内**，写在外面会对无该键的行 KeyError 并让整个 triage 崩溃。
- **年代证据是硬门槛（§2.1）**：Commons 侧非开放获取机构的文件，必须 `creator_death_year ≤ 1955` 或 `publication_year ≤ 1930`，且**必须是可解析的整数年份**。Commons 的 `publication_year` 常是上传时间（如 2018）或「17th century」这类字符串——前者不是作品年代，**不能用**；后者不可解析，要折算成具体年份并在 `decision_reason` 里写明来源（如「文件页 circa 1600」）。拿不到就标 `review`，不要硬凑。
- **★§5.2 短边门槛是分剖面的**：默认 **768**；「640」只是 **8gb 剖面的放宽下限**，不是通用门槛。`make_kohya_structure.py` / `preflight.py` 都取该剖面 `resolution_buckets` 的最小值作门槛（16gb→768，8gb→640）。**后果**：按 640 建的数据集切到 16gb 会卡（2026-09-29 实测 00007=767、00024=740 被拦）；`00024` 原图本身仅 760 短边、无法挽救，已换为光琳《松岛图》(00050)，`00007` 重裁到 775 达标。
- **★训练机实况（2026-09-29）**：GPU 为 **NVIDIA H20 / 95GB**，属 **16gb 剖面**（不是 8gb）。该机 **Python 3.9.16**，而 kohya 要求 **≥3.10** → 必须先 `dnf install -y python3.11`（仓库有此包）再建 venv。`models/` 与 kohya 当时均缺失。
- **★首次训练已完成（2026-10-09，H20 95GB）**：2000/2000 步、**71 分钟**（§8.1 预算 1.5h 内）、`avr_loss=0.118`，产出 `decomineral_v1_16gb.safetensors`（82MB）+ 3 个 epoch 检查点，抽检图 32 张（每 250 步 × 4）。**尚未按 §9 及格线人工打分**——打分前不算完成最小实验。
- **★生成权重用 0.6 而非 SPEC §7 的 0.8**（用户 2026-10-10 同意，属记录在案的偏离）：0.7/0.8 会出大量**伪阿拉伯书法条带**。根因是训练图保留了细密画的文字栏/题记，LoRA 把「书页+文字」学成了风格。**降权重只是缓解，不是根治**（0.6 仍有残留）。根治方案：审计并**重裁掉所有训练图的文字栏**→重训。评估时四条 branch 里 ritual/water/court 效果都好，future 及格线 3 过但配色偏灰（future 本就不是训练主题，符合 §3.3 设计）。
- **★改提示词不需要重训**：提示词只在生成/采样阶段生效，不参与训练。2026-10-10 那次 68 分钟重训与上一版完全等价（同数据、同配置、同 seed，loss 都是 0.118）——属于白花机时。**只有改数据才需要重训。**
- **★SDXL 在 fp16 下必须开 `no_half_vae`**：否则 VAE 数值溢出——轻则采样图全黑，**重则因为 `cache_latents=true` 时开头缓存的 latents 就是坏的，整个训练建立在废数据上、LoRA 报废**。首次训练（2000 步/loss 0.118 看着正常）就因此产出 32 张全黑图，模型不可用。重训前还要**删掉旧的 latents 缓存**（`find data/train/images -name "*.npz" -delete`），否则会复用坏缓存。可用 `--sample_at_first` 在训练开始前先出一张图，2 分钟内验证 VAE 管线是否正常，别白等 71 分钟。
- **★该机 bf16 不可用**：`mixed_precision=bf16` 会在头几个 step 以 **SIGFPE（信号 8）** 崩溃，且没有 Python traceback（`env_check` 当时就提示「支持 bf16=? fp16=yes」）。改 `fp16` 后正常。这是 `hardware/16gb.yaml` 第 19 行「不支持则 fp16」许可的，不算偏离剖面。bitsandbytes 0.50.2 的 AdamW8bit 本身可用。
- **其它踩坑（均已修）**：kohya 的 `requirements.txt` 含 `-e .`，必须在其目录内 pip install；toml 里 `vae = ""` 会被当 HF repo id 联网找 VAE 而崩溃（删掉该键即用 checkpoint 自带 VAE）；`configs/` 被 `patch_configs.py` 改过后是「脏」的，同步代码必须先 `git checkout -- configs/ && git pull` 再重跑 patch。
- **16gb/SDXL 配置已就绪**：`configs/dataset_16gb.toml`（桶 768/896/1024、num_repeats 26）+ `configs/sdxl_lora_16gb.toml`（rank/alpha 16、bf16、lr 1e-4、grad_accum 4、2000 步）。**在 16gb.yaml 的 `preferred_base=flux1-dev` 与 `fallback_base=sdxl` 之间选了 SDXL**，理由：用户推理机为 8GB，FLUX LoRA 推理显存不足。两套 configs 并存但 SPEC §0.8 禁止混用，训练时靠 `--config_file` 二选一。
- **GPU 机初始化**：`scripts/init_gpu.sh [sd-scripts目录]`（6 段幂等：机器信息 → torch/CUDA → 克隆/更新 kohya → 装依赖 → 项目与 models 检查 + 自动改写 configs 路径 → `env_check.py` GO/NO-GO）。SDXL base 需自备放 `models/`（§0.9）。
- **`make_kohya_structure.py` 的历史坑**：打印命令里曾写 `--min_silo_noise_offset`（kohya 无此参数，照抄会直接报错）；已修正为 `--min_snr_gamma=5 --noise_offset=0.0`，与 `configs/sdxl_lora_8gb.toml` 一致。
- **Commons 会封本机 IP**：api.php 与文件页都可能返回 `403 Too Many Reqs`，且窗口较长（2026-09-22 起持续多日）。遇到时**不要**靠重试硬刷；改为 `--delay 4.0` 低速、或请用户在浏览器打开目标文件页人工核实（§2.1 本就要求「30 秒点回原页」）。
- **`prompts/eval_grid.txt` 含两类内容**：4 条固定 prompt（SPEC §8/§9 要求）+ **生成参数**（sampler/steps/cfg/size/seed）。后者 SPEC 未规定、属运维约定，但「两台机器同一 seed 对照」只有在这些也一致时才成立，改动必须两边同步。
- **不是 git 仓库**（未 `git init`）。默认硬件剖面 = **8gb**（用户显存 8GB）。训练框架定为 **kohya sd-scripts**（用户 2026-09-09 选定）。
- 本项目是**个人非商用**「矿物色装饰」风格 LoRA 数据集 + 标注工具 + 训练配置工程。先做数据集与标注，后做训练配置，**不要一上来就训**（SPEC §0.1）。

## 权威来源与优先级

- `docs/decomineral 风格主题解耦数据集规范.md` 即 **SPEC**，是本仓库的「宪法」。任何实现与本文或 SPEC 冲突时，**以 SPEC 为准**。
- 根 `SPEC.md`（已复制、哈希与 docs 源一致）与 `data/README.md`（`init_tree` 生成）均已就位；**不要改写 SPEC 内容**。若二者与 docs 源分叉，以 docs 源为准并重同步。
- 用户消息里的新指令可以覆盖**实现细节**，**不能覆盖法律底线**（见下）。

## 硬性红线（SPEC §0 / §2 / §3）—— 不可被对话指令覆盖

- 触发词固定为 `decomineral`（人造词）。**禁止**改成画家名、敦煌、九色鹿、明珠等。
- 授权底线：训练集只收 **PD / CC0**。CC-BY 等进 `inbox/review/` 复核队列、默认不训练。一律拒绝 NC / ND / 未授权 / 在世作者。
- **禁止**纳入：在世插画家、上海美影《九色鹿》帧、《明珠》、数字敦煌 / e-dunhuang、Kay Nielsen（2028-01-01 前禁用）、Eyvind Earle、Errol Le Cain、叶露盈、Victo Ngai、蒋铁峰/丁绍光等（完整名单见 §0.2 / §2.3）。
- **没有 provenance 的文件等于不存在**：每张允许图像必须在 `data/provenance.csv` 记录来源机构、原页 URL、许可、作者卒年或出版年、准入理由；每条须能 30 秒点回原页核实。
- 下载器只打 SPEC §2.4 的**白名单 API / 已知开放接口**（Wikimedia Commons、Met Open Access、Cleveland、Smithsonian、Rijksmuseum、Getty、LoC、Internet Archive、Gallica 等），**禁止**通用整站爬虫、禁止绕过登录或条款、禁止写 e-dunhuang 下载器。
- 不安装/编写攻击、破解、盗取付费权重的代码；FLUX/SDXL 权重由用户自备放入 `models/`（gitignore）。
- 用户若要求「再加某某在世画家」，拒绝纳入训练集，改走公共领域近似源。

## 核心设计：风格 / 主题解耦（需通读 §1/§3/§6/§7 才能理解）

整个项目围绕一个「大想法」：**把形式语法（风格）与画面内容（主题）彻底拆开**，让同一套矿物色装饰语法能被迁移到宗教、宫廷、自然、水、未来等不同主题而不塌陷。这个约束贯穿多处，改任何一处都要考虑其它：

- `decomineral` 触发词**只描述形式语法**（平涂、矿物色、纹样=形体、挂毯空间、闭合轮廓等），**绝不描述**佛/凤/龙/飞天/故事。
- 主题只通过 caption 的 SUBJECT 段与生成期提示词进入（§6.2、§7），后期可选概念 LoRA（`deco_ritual` / `deco_water` / `deco_future`）；**永远不把概念触发词写进风格集 caption**。
- 为防「宗教过重 → 未来/水下全开出莲花」，强制 **theme 配额**（§3.3：ritual/court/nature/water 各≥8、ornament≥6、machine_or_sky≥4；`future` 不是训练集主题，缺则保持 4，禁止用现代科幻补）。
- 同时强制 **风格家族配额**（§3.2：A 丝路壁画 / B 波斯印度细密画 / C 俄童话 / D 彩玻珐琅 / E 琳派金地 / F 纯图案 / G 其它 PD），目标入库 45–70 张训练图，同一面墙/同一页书最多 3 张裁切。
- **主题解耦失败的第一反应永远是：查 `theme.primary` 直方图，不是加 GPU、不是改触发词、不是爬在世画家**（§9/§11）。

## 目录与数据流（SPEC §4 / §5 / §6）

SPEC §4 的目录树以仓库根（`f:/pearl_LoRA`）为准，树首的 `decomineral/` 是项目名、**不是**额外要新建的子层（若拿不准先与用户确认，勿双重嵌套）。要建的结构含：`schema/caption.schema.json`、`hardware/{16gb,8gb}.yaml`、`prompts/generate_en.yaml`、`data/{provenance.csv, inbox/raw, inbox/review, rejected, crops, train/images, train/captions, concept_later}`、`scripts/*`、`models/`(gitignore)、`output/lora/`、`logs/`。

数据流是**带许可闸门与质量门的单向流水线**（§5、§6）：

```
白名单 API 下载 → inbox/raw/<file_id>/（原图+许可片段，算 sha256 去重，永不直接训练）
  → license_gate（非 PD/CC0 拒写 train；CC-BY 转 inbox/review，问题图连同理由留 rejected/）
  → 质量门（短边阈值、块效应/翻拍/水印/斑驳、风格匹配项<4 拒）→ 人工/半自动 crops/
  → train/images/NNNNN.{png,jpg} + 同名 .txt（英文 caption）+ 同名 .json（结构化标注）
```

每张训练图是 **三件套**（png + txt + json），txt 与 json 由同一 `caption.schema.json`（§6.1）约束。英文 caption 固定四段、逗号连接、**永远以小写 `decomineral style` 开头**：`decomineral style, <FORM GRAMMAR>, <SUBJECT NOUNS>, <PALETTE AND MEDIUM>`（§6.2）；FORM GRAMMAR 只能用 §6.2 白名单短语，画家名/博物馆名/洞窟号**只进 JSON 与 provenance，不进 `.txt`**；训练 caption 用英文，中文只写进 JSON 的 `notes_zh`（§0.5）。

## 硬件剖面（SPEC §8）—— 只读其一，禁止混用

- **当前环境默认用 `8gb.yaml`**（用户显存 8GB）；`16gb.yaml` 随骨架生成仅供切换，任何时刻只引用一个（§0.8）。
- `hardware/16gb.yaml`：首选 FLUX.1-dev LoRA、fallback SDXL；rank/alpha 16、bucket [768,896,1024]、max_steps ~2000、bf16、oom 降级序列见文。
- `hardware/8gb.yaml`：首选 SDXL、默认禁用 FLUX；rank/alpha 8、bucket [640,768,832]、fp16、vae_slicing、短边 768 即可。
- 训练脚本只引用其中一个剖面；两台机器用同一随机种子做 4 条 branch 抽检对照（§8 末、§9）。

## 落地顺序（SPEC §10）—— 按 PR 顺序，每步可独立运行

- 第 0 步（冒烟前置，本仓库新增）：`env_check.py`——体检 GPU 机（nvidia-smi / torch.cuda / 显存→剖面 / `models` SDXL 权重 / kohya 入口 / 骨架），给 **GO/NO-GO**。
1. ✅ `init_tree.py`：建 §4 目录树 + 空 `provenance.csv` + 两个 hardware yaml + `caption.schema.json`（目录可建、schema 可校验，内置 jsonschema 自检）。
2. ✅ `license_gate.py`：铁律——只有 PD/CC0 且卒年≤1955 或美国出版年≤1930 才 `train`；CC-BY/no-known-restrictions 进 review；NC/ND/ARR/e-dunhuang/Kay Nielsen(至2028) 拒/review。支持 `--csv` 校验与 `--inbox` 从 `meta.json` 生成行。**`--inbox` 重建行时粘性保留人工策展字段**（`train_filename`/`family`/`theme_primary`/`creator`/卒年/出版年/`decision`/`decision_reason`，2026-09-15 修复：此前整行替换会丢这些字段、打断三件套↔provenance 链接）；许可变差时 `train` 判定回落自动分类。
3. ✅ `fetch_met.py`（Met Open Access API 按关键词拉 CC0 候选；含「平面作品门」剔除雕塑/石碑/器物等 3D 对象；只进 inbox/raw 候选，不自动当 train）。
4. ✅ `fetch_commons.py`（Commons 逐文件核 LicenseShortName 为 PD/CC0，存 file page url；仍须 license_gate + 人工核原页）。
5. ✅ `caption_lint.py`（§6.3 全项 + §3.3 配额；`--smoke` 仅把配额降为 WARN，法律/黑名单/前缀仍硬 FAIL）。
6. ✅ `make_kohya_structure.py`（**先过 provenance 法律门**：待训图无记录 / 非 train / 非 PD-CC0 / 缺 `.txt` → BLOCK；据剖面**只打印** kohya 训练命令、不代跑）。
7. ✅ `crop_assist.py`（§10 第 7 步：自动去边**仅作建议**，产出 `data/crops/` 建议图 + `_proposals.json`，入册前必须人工看图确认）。

**SPEC 原文：在第 1–2 步完成前不要写训练启动器。** 本仓库第 1–2 步已完成，第 6 步（训练启动器）也已在，但它是**为冒烟、按用户知情压缩顺序**落地，且内含法律门；正式训练仍须走满 §9（≥36 张 + theme 配额 + 无 `--smoke` 的 `caption_lint` 通过）。

## 常用命令（已实现脚本）

- **训练前自检（一条命令 GO/NO-GO）**：`python scripts/preflight.py [--profile 8gb] [--skip-gates]` —— 三件套完整性 + json 字段/split + §3.3 配额 + §5.2 短边 + 册/图双向链接 + val 未混入 + metadata 条数 + 三道门。退出码 0=GO（允许有 WARN）、1=NO-GO。**开训前先跑这个。**
- **GPU 机路径适配**：`python scripts/patch_configs.py --project-dir /root/pearl_LoRA [--model .../sd_xl_base_1.0.safetensors] [--dry-run]` —— 把 `configs/*.toml` 里的 Windows 绝对路径改写成目标机路径（幂等；`models/` 下只有一个 safetensors 时自动探测）。`init_gpu.sh` 第 5 段会自动调用。

- 体检 GPU 训练机（冒烟第一步）：`python scripts/env_check.py [--sd-scripts PATH]` —— stdlib-only，缺 GPU/torch/kohya 优雅降级，末尾 GO/NO-GO。
- 初始化/补骨架（幂等）：`python scripts/init_tree.py [--force]` —— 建 §4 目录 + 生成 schema/csv/yaml/prompts/data README，内置 schema 自检。
- Met 精取（**检索已退化，优先用这个**）：`python scripts/_probe_met.py --ids 452651,451726`（只探查不下载，打印 title/objectName/medium）→ 选定后 `python scripts/fetch_met.py --ids 452651,451726` 正式下载。
- Commons 全文检索（主力）：`python scripts/fetch_commons.py --search "Kalila wa Dimna manuscript" --limit 6 --delay 4.0`（分类浏览 `--category` 只给字母序前 N 条，命中面窄；限流时先退避 30–60s）。
- 拉取候选：`python scripts/fetch_met.py --query "Shahnama miniature" [--query X --limit N --delay S]` —— Met Open Access，只收 isPublicDomain(CC0)，含平面作品门；进 `data/inbox/raw`。
- Commons 抓取：`python scripts/fetch_commons.py --category "Category:Persian miniatures" [--limit N]` —— 逐文件核许可 PD/CC0，存 file page url。
- 许可闸门：`python scripts/license_gate.py --csv data/provenance.csv`（校验既有行）或 `--inbox data/inbox/raw --csv data/provenance.csv`（从 `meta.json` 生成行）。
- 标注校验：`python scripts/caption_lint.py --train data/train/images [--smoke]` —— 见「校验要点」。
- 裁切建议：`python scripts/crop_assist.py [--ids met_44794 ...] [--bbox met_44794:120,300,1900,3800]` —— 只给建议，须人工确认；依赖 Pillow。
- 生成训练结构/命令：`python scripts/make_kohya_structure.py --profile 8gb [--smoke --allow-small --steps N --model PATH]` —— 法律门 + 可选尺寸门，写 `metadata.json`、打印 kohya 命令到 `logs/smoke_train_cmd.txt`，**不代跑**。
- 正式训练（GPU 机，走 `configs/`）：`accelerate launch --num_cpu_threads_per_process 2 sdxl_train_network.py --config_file F:/pearl_LoRA/configs/sdxl_lora_8gb.toml --dataset_config F:/pearl_LoRA/configs/dataset_8gb.toml`（`make_kohya_structure` 打印的老命令行仅供参考，以 toml 为准）。
- 崩溃恢复：`python scripts/_recover_fill.py` —— 按 `data/crops/_ingest_map.csv` 幂等回填 `provenance.csv` 的 `train_filename` 并同步 `family`/`theme_primary`。

冒烟一次（4–8 张手工 PD/CC0 图入 `data/train/images` 三件套 + provenance `decision=train` 且 `train_filename` 已回填）：

```text
python scripts/env_check.py
python scripts/license_gate.py --csv data/provenance.csv
python scripts/caption_lint.py --train data/train/images --smoke
python scripts/make_kohya_structure.py --profile 8gb --smoke --allow-small --steps 10
```

## 校验要点（`caption_lint.py` 必须拦截，SPEC §6.3）

对每条 `.txt`：开头须为 `decomineral style`；不含黑名单词（`dunhuang style`、`mogao style`、`bilibin style`、`nielsen`、`ngai`、`ye luying`、`earle`、`le cain`、`nine-color`、`jiu se lu`、`ming zhu`、`anime`、`photoreal`、`8k`、`masterpiece` 等）；至少 1 个 FORM GRAMMAR 短语；至少 1 个 content 名词；JSON `theme.primary` 与 caption 大意不冲突（如 water 图须出现 water/wave/boat/fish/lotus-pond 之一）；统计 theme 分布，不满足 §3.3 配额则**失败退出**（`--smoke` 下配额降为 WARN）。另须保证 `.json` 通过 `schema/caption.schema.json`。

## 约定与注意

- **v1.1 语法扩展（SPEC §13，2026-09-14）**：`style.traits` 与 FORM GRAMMAR 新增装饰画传统技法词条 `patterned_terrain`（山体满铺纹理=树林）/`radial_gradient`（中心向外轮环渐变）/`nonfocal_figures`（非焦点大面积人物制造张力）及对应英文短语；配色仍用 `palette` 矿物色枚举。已在 SPEC/`schema/caption.schema.json`/`scripts/init_tree.py`/`scripts/caption_lint.py`/`prompts/generate_en.yaml` 同步，**后续改语法须保持这五处一致**。这些词条属公共领域装饰画传统方法总结，不含任何受版权保护作品。
- 训练框架**已定为 kohya sd-scripts**（用户 2026-09-09；`make_kohya_structure.py` 据此生成 `sdxl_train_network.py` 命令）。SPEC §12 说框架「由当时环境决定」，故仓库不固定 Python 依赖、无 `requirements.txt`/`pyproject.toml`；本仓库 5 个脚本仅用标准库（`caption_lint`/`env_check`/`make_kohya_structure` 可选用 `jsonschema`/`Pillow`/`PyYAML`，缺则降级跳过）。SDXL base 权重由用户自备放 `models/`（§0.9）。
- 下载器须写清 User-Agent 与联系方式、遵守各站速率（Met 官方 ~80 req/s，本项目实跑用 1–2 req/s，§5.1）。
- val 集留 4–6 张、覆盖不同 family 与 theme、不参与训练（§6.1）。
- 生成期拼法：`<lora:decomineral:0.8>, {style_lock}, {subject}, malachite, azurite, cinnabar, gold`（§7）。
