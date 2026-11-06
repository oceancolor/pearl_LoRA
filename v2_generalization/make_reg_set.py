#!/usr/bin/env python
"""生成先验保留负例集（reg set），用 base SDXL 出通用图 + 普通 caption。

用途：v1 训练 100% 图都是同风格、0 张负例，LoRA 无条件改变输出分布
（"任何提示词都出几何装饰画"）。把本脚本产出的通用图作为第二个 subset
混入训练，直接教模型"无触发词时保持 base 先验"。

用 kohya sdxl_gen_img.py 生成（离线、fp32；fp16 在本机 H20 上会出黑图）。

用法:
  /root/workspace/benjamin/venv/bin/python make_reg_set.py [--n 24]
输出:
  /root/workspace/benjamin/next_train/reg_set/images/NNNNN.png + 同名 .txt
"""
import argparse
import glob
import os
import shutil
import subprocess

B = "/root/workspace/benjamin"
OUT = B + "/next_train/reg_set/images"

# (生成用 prompt, 训练用 caption)：无触发词、无风格词、无 pattern/deco 语义
PROMPTS = [
    ("a photorealistic portrait of an elderly fisherman, weathered face, natural light, 50mm photo",
     "a photorealistic portrait of an elderly fisherman with a weathered face, natural light"),
    ("a bowl of ramen with soft egg and scallions on a wooden table, food photography, soft light",
     "a bowl of ramen with a soft egg and scallions on a wooden table, food photography"),
    ("a modern city street at dusk with cars and neon signs, cinematic lighting",
     "a modern city street at dusk with cars and glowing neon signs, cinematic lighting"),
    ("a golden retriever puppy running across green grass in a park, photograph",
     "a golden retriever puppy running across green grass in a sunny park, photograph"),
    ("a red rowing boat moored at a wooden dock on a calm lake, morning mist, photograph",
     "a red rowing boat moored at a wooden dock on a calm lake, light morning mist, photograph"),
    ("an old brick library interior with tall wooden shelves and a reading table, warm daylight",
     "an old brick library interior with tall wooden shelves and a long reading table, warm daylight"),
    ("a rusty vintage tractor parked in a field of dry grass, overcast sky, photograph",
     "a rusty vintage tractor parked in a field of dry grass under an overcast sky, photograph"),
    ("a cup of black coffee beside a notebook and pen on a white desk, top down photo",
     "a cup of black coffee beside an open notebook and a pen on a white desk, top down photo"),
    ("a mountain hiker with a backpack standing on a rocky ridge at sunrise, photograph",
     "a hiker with a backpack standing on a rocky mountain ridge at sunrise, photograph"),
    ("a steaming plate of dumplings in a blue ceramic dish on a dark restaurant table",
     "a steaming plate of dumplings served in a blue ceramic dish on a dark restaurant table"),
    ("a green frog sitting on a wet leaf in a garden after rain, macro photograph",
     "a green frog sitting on a wet leaf in a garden after rain, macro photograph"),
    ("a crowded farmers market stall with fruit crates and hanging signs, daylight photo",
     "a busy farmers market stall with crates of fruit and hanging signs, daylight photograph"),
    ("a single sailboat far offshore under a clear blue sky, calm sea, photograph",
     "a single white sailboat far offshore under a clear blue sky on a calm sea, photograph"),
    ("a mechanic working under a car in a small garage full of tools, warm light, photo",
     "a mechanic working under a car in a small garage filled with tools, warm light, photograph"),
    ("a snowy village road lined with pine trees at blue hour, footprints in the snow",
     "a snowy village road lined with pine trees at blue hour, fresh footprints in the snow"),
    ("a white horse trotting through shallow water at the edge of a beach, photograph",
     "a white horse trotting through shallow water at the edge of a sandy beach, photograph"),
    ("an elderly potter shaping a clay bowl on a spinning wheel, dusty workshop, daylight",
     "an elderly potter shaping a clay bowl on a spinning wheel in a dusty workshop, daylight"),
    ("a hot air balloon drifting above patchwork farmland in early morning light",
     "a hot air balloon drifting above patchwork farmland in soft early morning light, photo"),
    ("a jazz quartet playing on a small club stage with warm spotlights, photograph",
     "a jazz quartet performing on a small club stage under warm spotlights, photograph"),
    ("a fallen log covered with moss in a dense green forest, shafts of light, photo",
     "a fallen log covered with moss in a dense green forest with shafts of light, photograph"),
    ("a yellow taxi waiting at a rainy intersection at night, reflections on wet asphalt",
     "a yellow taxi waiting at a rainy city intersection at night with reflections on wet asphalt"),
    ("a wooden rowboat upside down on a lawn beside a small cottage, summer afternoon",
     "a wooden rowboat turned upside down on a lawn beside a small cottage, summer afternoon"),
    ("a chef plating pasta in a professional kitchen with steel counters, candid photo",
     "a chef plating pasta in a professional kitchen with steel counters, candid photograph"),
    ("a paper lantern glowing on a quiet temple path in the evening, photograph",
     "a single paper lantern glowing on a quiet stone temple path in the evening, photograph"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--steps", type=int, default=25)
    args = ap.parse_args()
    n = min(args.n, len(PROMPTS))
    os.makedirs(OUT, exist_ok=True)

    raw = "/tmp/reg_raw"
    shutil.rmtree(raw, ignore_errors=True)
    os.makedirs(raw, exist_ok=True)
    pf = "/tmp/reg_prompts.txt"
    with open(pf, "w") as f:
        f.write("\n".join(p for p, _ in PROMPTS[:n]) + "\n")

    env = os.environ.copy()
    env.update({
        "HF_HOME": B + "/cache/hf",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "TMPDIR": B + "/tmp",
    })
    cmd = [
        B + "/venv/bin/python", B + "/sd-scripts/sdxl_gen_img.py",
        "--ckpt", B + "/models/sd_xl_base_1.0.safetensors",
        "--from_file", pf,
        "--W", "896", "--H", "896",
        "--steps", str(args.steps), "--sampler", "euler_a",
        "--seed", "20261106", "--images_per_prompt", "1",
        "--outdir", raw, "--sdpa",
    ]
    print("[reg] generating with base SDXL (kohya, fp32, offline)...", flush=True)
    with open("/tmp/reg_gen.log", "w") as log:
        rc = subprocess.call(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
    if rc != 0:
        raise SystemExit(f"[reg] generation failed rc={rc}, see /tmp/reg_gen.log")

    files = sorted(glob.glob(raw + "/*.png"))
    if len(files) < n:
        raise SystemExit(f"[reg] only {len(files)}/{n} images generated")
    for i, (src, (_, cap)) in enumerate(zip(files[:n], PROMPTS[:n]), 1):
        name = f"{i:05d}"
        shutil.move(src, os.path.join(OUT, name + ".png"))
        with open(os.path.join(OUT, name + ".txt"), "w") as f:
            f.write(cap)
        print(f"[reg] {name}.png <- {cap[:62]}...", flush=True)
    print(f"[reg] done: {n} images -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
