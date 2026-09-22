# decomineral — 矿物色装饰 · 风格 / 主题解耦 LoRA

个人非商用风格 LoRA 项目：用**公共领域装饰绘画**抽出可迁移的**形式语法**（平涂、矿物色、纹样=形体、挂毯空间、闭合轮廓），
再以同一套语法生成宗教仪轨 / 未来宫殿 / 水世界等主题。触发词 `decomineral` **只描述风格、绝不描述主题**。

## 权威文档
- **`SPEC.md`**（根目录，与 `docs/decomineral 风格主题解耦数据集规范.md` 同源）= 本项目宪法。动手前先读 SPEC，再读 `data/README.md`。
- 法律底线**不可被对话指令覆盖**（SPEC §0 / §2）。

## 红线速览（详见 SPEC §0 / §2 / §3）
- 触发词固定 `decomineral`，禁止改成画家名 / 敦煌 / 九色鹿 / 明珠。
- 训练集仅 **PD / CC0**；禁在世作者；下载只打 §2.4 白名单，禁整站爬虫与 e-dunhuang。
- **没有 provenance 的图 = 不存在**；风格与主题必须解耦。

## 当前环境
- GPU 显存 **8GB** → 训练/生成使用 `hardware/8gb.yaml`（SDXL LoRA 首选，默认禁用 FLUX）。
  `hardware/16gb.yaml` 随骨架生成供切换，但**任何时刻只引用一个剖面，勿混用**（SPEC §0.8）。

## 目录骨架（由 `scripts/init_tree.py` 生成，SPEC §4）
- `schema/caption.schema.json` — caption JSON Schema（§6.1）
- `hardware/{8gb,16gb}.yaml` — 硬件剖面（§8）
- `prompts/generate_en.yaml` — 生成期提示词合同（§7）
- `data/` — 数据流水线与 provenance 账本（见 `data/README.md`）
- `scripts/` — 工具脚本，落地顺序见 SPEC §10

## 快速开始
```text
python scripts/init_tree.py            # 建/补目录骨架（幂等；--force 重写生成物）
python scripts/env_check.py            # 体检 GPU 训练机（GO/NO-GO；缺依赖优雅降级）
python scripts/license_gate.py --csv data/provenance.csv            # 法律门：非 PD/CC0 不得 train
python scripts/caption_lint.py --train data/train/images [--smoke]  # caption/配额门禁
python scripts/make_kohya_structure.py --profile 8gb [--smoke]      # 打印训练命令，不代跑
python scripts/fetch_met.py --query "Shahnama miniature" --limit 6   # Met CC0 候选→inbox/raw（含平面作品门）
python scripts/fetch_commons.py --category "Category:Persian miniatures" --limit 6  # Commons PD/CC0 候选
```
落地顺序（SPEC §10）：env_check(冒烟前置) → init_tree → license_gate → fetch_met/fetch_commons(取数) → caption_lint → make_kohya_structure；人工裁切辅助（§10 第7步）尚未实现。
**先做数据集与标注，最后做训练配置；正式训练须走满 §9（≥36 张 + theme 配额 + 无 --smoke 的 caption_lint 通过）。**
