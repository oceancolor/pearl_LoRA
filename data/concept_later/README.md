# 概念 LoRA 数据集（deco_ritual / deco_water / deco_future）

依据 SPEC §7 末：

> 概念 LoRA 只在风格 LoRA 稳定后做，每支 15–25 张，触发词另起：`deco_ritual` `deco_water` `deco_future`。永远不要把概念触发词写进风格集 caption。

**前置条件已满足**：风格 LoRA `decomineral_v1_16gb`（v3）已于 2026-10-10 通过 §9 最小实验（ritual / court / water / future 四条 branch 及格）。

---

## 1. 目录

```
data/concept_later/
  ritual/        -> deco_ritual   15–25 张三件套（png + txt + json）
  water/         -> deco_water    15–25 张
  future_seed/   -> deco_future   15–25 张（「幻想」向，见 §3）
```

三件套格式与风格集一致（`NNNNN.png` + `NNNNN.txt` + `NNNNN.json`），json 走同一 `schema/caption.schema.json`。

## 2. 触发词规则（硬性）

1. caption **第一个词**就是概念触发词：`deco_ritual, ...` / `deco_water, ...` / `deco_future, ...`
2. **永远不要把概念触发词写进风格集 caption**（`data/train/images/`）—— SPEC 原文，违反会污染风格 LoRA
3. 反向同理（本项目约定）：概念集 caption **不写风格锁词**（`decomineral style` / `flat mineral pigments` / `no chiaroscuro` / `pattern equal to form` / `tapestry space` / `jewel-like palette` / `closed color shapes` / `ornamental border`）。
   风格由风格 LoRA 负责，概念 LoRA 只负责「画面里有什么」——解耦是双向的，这是从 §7「主题靠 caption 与后期概念 LoRA，不靠把主题写进触发词」推导出来的
4. caption 其余部分只写**内容物**（名词罗列），与风格集同一写法

## 3. 各概念的素材标准

### deco_ritual —— 仪典 / 圣像 / 供养
华盖、宝座、坛场、供养人行列、幡幢、背光、护法、圣树、供养器。
（宗教仪轨意象本身是允许的，这是 ritual 的定义。）

### deco_water —— 水 / 浪 / 舟 / 鱼 / 水下宫
浪脊、泡沫、池、鱼、舟、莲、水下宫、河岸、洲渚。

### deco_future —— **幻想，不是科幻**（用户 2026-10-19 定的标准）

> 严格限制的是**科技类**素材，而不是奇幻、梦幻类素材。

- **允许**：天宫楼阁、云端宫殿、空中台阁、塔幢、须弥山、神兽异兽（龙、Simurgh、麒麟、凤凰）、仙人车驾、云车、云气、星象 / 星宿、火焰轮环、羽人、异境山水
- **禁止**：机械、齿轮、飞船 / 火箭、机器人、金属仪表、电路、科技界面，以及任何现代科幻插画
  —— 与 SPEC §3.3「禁止用现代科幻插画补」一致；本项目在此基础上进一步限定为「幻想」而非「科幻」

## 4. 门槛（与风格集同标准）

- 法律：provenance 记录 + PD/CC0 + 年代证据（§2.1）
- 尺寸：短边门槛**分剖面**（§5.2）——16gb 剖面 **≥768**，8gb 剖面 ≥640
- 画质：拒翻拍、展厅照、黑白珂罗版、块效应、大面积泥底裸露；**带文字栏的书页要裁掉文字部分**（风格 LoRA 已因文字栏残留吃过亏：生成伪阿拉伯书法）

## 5. 现成可用（2026-10-19 预筛）

| 概念 | 现成张数 | 来源 |
|---|---|---|
| deco_ritual | 8 | 风格集 ritual：00007 00008 00009 00033 00034 00035 00042 00049 |
| deco_water | 8 | 风格集 water：00022 00028 00029 00030 00031 00032 00045 00050 |
| deco_future | ~10 候选 | 00016（山间塔楼+云，最贴）、00020（屠龙）、00021（Simurgh 神鸟）、00033/00034/00035/00042（云气、火焰轮环、华盖、背光）、00043（宫台）、00049（火审）、00001（群鸟） |

**复用说明**：同一张图可以同时服务风格集与概念集（两者学的东西不同），但概念集需有**独立的 caption 文件**（带触发词）。数据有限时允许复用，优先补新图。

## 6. 缺口

每支需 15–25 张，即总计 45–75 张。现有可复用约 26 张次，**仍需新补 20–50 张**。

## 7. 待办

- [ ] D：按 §3 标准补图（下载 → 目检 → 裁切 → caption → 入册 → 过门）
- [ ] C：概念 LoRA 训练配置（`configs/`）+ 训练/出图脚本
