#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_kohya_structure.py — 冒烟/训练前：法律门 + 组装 kohya sd-scripts 训练结构（SPEC §10 第 6 步）。

做三件事（不执行训练，只准备 + 打印命令；SPEC §0.1 别一上来就训）：
  1) 法律前置门：data/train/images/ 每个待训图都必须在 provenance.csv 有
     decision=train 且 license∈{PD,CC0}，且同名 .txt 存在。违例即 BLOCK 退出（§0.3/§2）。
  2) 质量门（可选）：装了 Pillow 时核短边 >= 剖面最小值（8gb=640，§5.2）；--allow-small 冒烟放行。
  3) 组装：写 data/train/images/metadata.json（kohya 可读），打印 SDXL sdxl_train_network 训练
     命令（取自 hardware/8gb.yaml），并落盘 logs/smoke_train_cmd.txt。

用法：
    python scripts/make_kohya_structure.py --profile 8gb
    python scripts/make_kohya_structure.py --profile 8gb --smoke --allow-small
"""

import argparse
import csv
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
IMG_EXTS = (".png", ".jpg", ".jpeg")
TRAIN_OK = {"PD", "CC0"}
KEEP_TOKENS = 2  # 'decomineral style' 固定前缀


def load_profile(name):
    """读 hardware/<name>.yaml；优先 PyYAML，缺失则最小解析所需标量。"""
    p = ROOT / "hardware" / ("%s.yaml" % name)
    if not p.exists():
        raise SystemExit("找不到 %s（先跑 init_tree.py）" % p)
    text = p.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except Exception:
        pass
    prof = {"profile": name, "train": {}, "lora": {}}
    import re
    def grab(key, cast=str, default=None):
        m = re.search(r"^\s*%s:\s*(.+?)\s*(?:#.*)?$" % re.escape(key), text, re.M)
        if not m:
            return default
        val = m.group(1).strip().strip('"\'')
        if cast is float:
            try:
                return float(val)
            except Exception:
                return default
        if cast is int:
            try:
                return int(val)
            except Exception:
                return default
        return val
    prof["preferred_base"] = grab("preferred_base")
    prof["lora"]["rank"] = grab("rank", int, 8)
    prof["lora"]["alpha"] = grab("alpha", int, 8)
    prof["train"]["batch_size"] = grab("batch_size", int, 1)
    prof["train"]["grad_accum"] = grab("grad_accum", int, 8)
    prof["train"]["optimizer"] = grab("optimizer", str, "adamw8bit")
    prof["train"]["lr"] = grab("lr", float, 8.0e-5)
    prof["train"]["max_train_steps"] = grab("max_train_steps", int, 1800)
    prof["train"]["mixed_precision"] = grab("mixed_precision", str, "fp16")
    m = re.search(r"resolution_buckets:\s*\[([^\]]+)\]", text)
    prof["train"]["resolution_buckets"] = [int(x) for x in m.group(1).split(",")] if m else [640, 768, 832]
    prof["train"]["gradient_checkpointing"] = "gradient_checkpointing: true" in text
    prof["train"]["cache_latents"] = "cache_latents: true" in text
    prof["train"]["vae_slicing"] = "vae_slicing: true" in text
    return prof


def load_provenance():
    pp = ROOT / "data" / "provenance.csv"
    out = {}
    if not pp.exists():
        return out
    for r in csv.DictReader(open(pp, encoding="utf-8")):
        tf = (r.get("train_filename") or "").strip()
        if tf:
            out[Path(tf).name] = r
    return out


def short_side(path):
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None
    try:
        with Image.open(path) as im:
            return min(im.size)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="decomineral kohya 结构生成器")
    ap.add_argument("--profile", default="8gb", choices=["8gb", "16gb"])
    ap.add_argument("--images", default=str(ROOT / "data/train/images"))
    ap.add_argument("--smoke", action="store_true", help="冒烟：steps 调极小、放宽配额告警")
    ap.add_argument("--steps", type=int, default=None, help="覆盖 max_train_steps（冒烟建议 5-20）")
    ap.add_argument("--allow-small", action="store_true", help="允许短边不足（仅冒烟，须心里有数）")
    ap.add_argument("--model", default=None, help="SDXL base 路径（默认提示用户填 models/）")
    args = ap.parse_args()

    prof = load_profile(args.profile)
    images_dir = Path(args.images)
    if not images_dir.exists():
        raise SystemExit("images 目录不存在：%s" % images_dir)

    prov = load_provenance()
    imgs = sorted([p for p in images_dir.iterdir()
                   if p.suffix.lower() in IMG_EXTS and p.is_file()])

    legal_block, missing_txt, size_warn = [], [], []
    min_side = 768 if args.profile == "16gb" else 640
    for img in imgs:
        base = img.name
        rec = prov.get(base)
        if not rec:
            legal_block.append("%s: 无 provenance 记录（没 provenance = 不存在，§0.3）" % base)
            continue
        lic = (rec.get("license") or "").strip().upper()
        dec = (rec.get("decision") or "").strip().lower()
        if dec != "train" or lic not in TRAIN_OK:
            legal_block.append("%s: provenance decision=%s license=%s 非 train/PD-CC0（§2）" % (base, dec or "?", lic or "?"))
            continue
        if not img.with_suffix(".txt").exists():
            missing_txt.append(base)
        side = short_side(img)
        if side is not None and side < min_side:
            size_warn.append("%s 短边=%d < %d（§5.2）" % (base, side, min_side))

    print("== make_kohya_structure（profile=%s, 发现 %d 张图）==" % (args.profile, len(imgs)))

    if missing_txt:
        print("[BLOCK] 缺同名 .txt（caption，§6）：\n   - " + "\n   - ".join(missing_txt))
    if legal_block:
        print("[BLOCK] 法律/许可前置门未过（§0.3/§2）：\n   - " + "\n   - ".join(legal_block))
    if size_warn:
        lvl = "WARN" if (args.smoke and args.allow_small) else "BLOCK"
        print("[%s] 短边不足：\n   - %s" % (lvl, "\n   - ".join(size_warn)))

    if legal_block or missing_txt:
        print("-" * 60)
        print("训练结构未生成。先过 license_gate（decision=train）+ 补 .txt caption，再重跑。")
        sys.exit(3)
    if size_warn and not (args.smoke and args.allow_small):
        print("加 --smoke --allow-small 仅为冒烟放行；正式须重裁（§5.2/§5.3）。")
        sys.exit(4)

    # 组装 metadata.json（kohya 新版可读；同时 .txt 也在旁边供 --caption_extension）
    meta = {}
    for img in imgs:
        rec = prov.get(img.name, {})
        cap = img.with_suffix(".txt").read_text(encoding="utf-8").strip() if img.with_suffix(".txt").exists() else ""
        if not cap:
            cap = rec.get("caption_en", "")
        meta[img.name] = {"full_path": str(img), "caption": cap, "repeats": 1, "keep_tokens": KEEP_TOKENS}
    (images_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[OK] 写 metadata.json：%d 条（keep_tokens=%d）" % (len(meta), KEEP_TOKENS))
    if len(meta) < 36:
        print("     注：train=%d 张，满足冒烟（>=4），未满足 §9 最小实验(>=36)。" % len(meta))

    steps = args.steps if args.steps is not None else prof["train"]["max_train_steps"]
    if args.smoke and args.steps is None:
        steps = 10  # 冒烟默认极小，先验证不崩/不 OOM
    tr = prof["train"]
    bucket = ",".join(str(b) for b in tr.get("resolution_buckets", [640, 768]))
    model = args.model or "MODELS/sdxl-base-REPLACE_ME"
    cmd = [
        "accelerate launch --num_cpu_threads_per_process 2 sdxl_train_network.py",
        "--pretrained_model_name_or_path=\"%s\"" % model,
        "--train_data_dir=\"%s\"" % str(images_dir),
        "--caption_extension=.txt",
        "--keep_tokens=%d" % KEEP_TOKENS,
        "--network_module=networks.lora",
        "--network_dim=%s" % prof["lora"].get("rank", 8),
        "--network_alpha=%s" % prof["lora"].get("alpha", 8),
        "--train_batch_size=%s" % tr.get("batch_size", 1),
        "--gradient_accumulation_steps=%s" % tr.get("grad_accum", 8),
        "--max_train_steps=%d" % steps,
        "--learning_rate=%s" % tr.get("lr", 8.0e-5),
        "--lr_scheduler=cosine",
        "--optimizer_type=AdamW8bit",
        "--mixed_precision=%s" % tr.get("mixed_precision", "fp16"),
        "--enable_bucket --bucket_resolution=%s" % bucket,
        "--save_model_as=safetensors",
        "--output_dir=\"%s\"" % str(ROOT / "output/lora"),
        "--output_name=decomineral_smoke",
    ]
    flags = ["--gradient_checkpointing" if tr.get("gradient_checkpointing") else None,
             "--cache_latents" if tr.get("cache_latents") else None,
             "--vae_slicing" if tr.get("vae_slicing") else None]
    cmd += [f for f in flags if f]
    # 注：旧版这里写成 --min_silo_noise_offset（kohya 无此参数，会直接报错退出）。
    # 正确名是 --min_snr_gamma，取值与 configs/sdxl_lora_8gb.toml 一致（SPEC §8.2）。
    cmd += ["--min_snr_gamma=%s" % tr.get("min_snr_gamma", 5),
            "--noise_offset=%s" % tr.get("noise_offset", 0.0),
            "--max_data_loader_n_workers=2 --persistent_data_loader_workers"]

    text = " \\\n  ".join(cmd)
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    (logs / "smoke_train_cmd.txt").write_text(text + "\n", encoding="utf-8")
    print("-" * 60)
    print("训练命令（已写 logs/smoke_train_cmd.txt；本工具不会代跑，请你在 GPU 机核对后手动执行）：\n")
    print(text)
    print("\n[提醒] 把 \"%s\" 换成 models/ 里真实 SDXL base 路径；FLUX 权重在 8GB 默认禁用（§8.2）。" % model)
    if args.smoke:
        print("[提醒] 这是冒烟：steps=%d。产物 output/lora/decomineral_smoke 不可当成品对外，" % steps)
        print("       正式须补到 >=36 张、theme 配额、caption_lint 无 --smoke 通过（§9）。")
    sys.exit(0)


if __name__ == "__main__":
    main()
