#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_configs.py — 把 configs/*.toml 里的 Windows 绝对路径改写成当前机器路径。

本机（Windows）configs 里写的是 F:/pearl_LoRA/...；GPU 机（Linux）路径不同，
手改容易漏/错。本脚本统一把项目根替换掉，并可指定 SDXL base 权重路径。
幂等：重复运行结果相同。

用法：
    python scripts/patch_configs.py --project-dir /root/pearl_LoRA
    python scripts/patch_configs.py --project-dir /root/pearl_LoRA \
        --model /root/pearl_LoRA/models/sd_xl_base_1.0.safetensors
    python scripts/patch_configs.py --project-dir . --dry-run   # 只看会改什么
"""
import argparse
import pathlib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parents[1]
WIN_ROOT_RE = re.compile(r"[A-Za-z]:[\\/]pearl_LoRA", re.IGNORECASE)


def main():
    ap = argparse.ArgumentParser(description="改写 configs 里的绝对路径")
    ap.add_argument("--project-dir", required=True, help="当前机器上的项目根")
    ap.add_argument("--model", default=None, help="SDXL base 权重绝对路径（可选）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    proj = pathlib.Path(args.project_dir).expanduser().resolve()
    if not (proj / "data" / "train" / "images").is_dir():
        print("[WARN] %s 下未见 data/train/images，确认项目根是否正确" % proj)

    model = args.model
    if model is None:
        cands = sorted((proj / "models").glob("*.safetensors"))
        model = str(cands[0]) if cands else None
        if model:
            print("自动探测到 SDXL base：%s" % model)
        else:
            print("[WARN] models/ 下未找到 .safetensors，将保留原 pretrained_model_name_or_path")

    targets = {
        "configs/dataset_8gb.toml": [("image_dir", proj / "data" / "train" / "images")],
        "configs/sdxl_lora_8gb.toml": [("output_dir", proj / "output" / "lora"),
                                       ("logging_dir", proj / "logs")],
    }
    if model:
        targets["configs/sdxl_lora_8gb.toml"].insert(
            0, ("pretrained_model_name_or_path", pathlib.Path(model)))

    for rel, keys in targets.items():
        p = ROOT / rel
        if not p.exists():
            print("  ! 缺失 %s" % rel)
            continue
        text = p.read_text(encoding="utf-8")
        new = WIN_ROOT_RE.sub(str(proj).replace("\\", "/"), text)
        for key, val in keys:
            pat = re.compile(r'(?m)^(\s*%s\s*=\s*)"[^"]*"' % re.escape(key))
            rep = r'\1"%s"' % str(val).replace("\\", "/")
            new, n = pat.subn(rep, new)
            if n == 0:
                print("  ! %s 未找到键 %s" % (rel, key))
        if new == text:
            print("  = %s 无变化" % rel)
            continue
        print("  ~ %s" % rel)
        if not args.dry_run:
            p.write_text(new, encoding="utf-8")

    print("-" * 60)
    print("done%s" % ("（dry-run，未写盘）" if args.dry_run else ""))


if __name__ == "__main__":
    main()
