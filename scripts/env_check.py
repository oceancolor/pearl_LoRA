#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""env_check.py — decomineral 训练机环境体检（冒烟前置，SPEC §0.8 / §8.2 / §0.9）。

目的：在“已申请到的 GPU 环境”上跑它，回答“今晚能不能冒烟训练一次”。
设计：尽量只用标准库；torch / nvidia-smi / kohya 缺失都优雅降级，不崩。

用法（在 GPU 机器上）：
    python scripts/env_check.py
    python scripts/env_check.py --sd-scripts /path/to/sd-scripts --models /path/to/models
"""

import argparse
import glob
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]

PASS, WARN, FAIL, INFO = "PASS", "WARN", "FAIL", "INFO"
_state = {}


def emit(level, msg):
    _state[level] = _state.get(level, 0) + 1
    print("[%s] %s" % (level, msg))


def vram_to_profile(total_gb):
    """显存 GB -> 推荐剖面（SPEC §8）。"""
    if total_gb is None:
        return None, "无法确定显存，按 8gb 保守（勿混用剖面，SPEC §0.8）。"
    if total_gb < 10:
        return "8gb", "显存 ~%dGB -> 用 hardware/8gb.yaml（SDXL 首选，默认禁 FLUX）。" % round(total_gb)
    if total_gb >= 14:
        return "16gb", "显存 ~%dGB -> 可用 hardware/16gb.yaml（FLUX 或 SDXL）。" % round(total_gb)
    return "8gb", "显存 ~%dGB 属灰区 -> 保守用 hardware/8gb.yaml。" % round(total_gb)


def check_python():
    v = sys.version_info
    ver = "%d.%d.%d" % (v.major, v.minor, v.micro)
    if v >= (3, 10):
        emit(PASS, "Python %s (%s/%s)" % (ver, platform.system(), platform.machine()))
    else:
        emit(WARN, "Python %s 偏旧，kohya 建议 >=3.10" % ver)


def check_nvidia_smi():
    if not shutil.which("nvidia-smi"):
        emit(FAIL, "找不到 nvidia-smi：此机可能无 NVIDIA GPU 或未装驱动 -> 今晚无法训练。")
        return None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=20)
    except Exception as exc:
        emit(FAIL, "nvidia-smi 调用失败：%s" % exc)
        return None
    if out.returncode != 0:
        emit(FAIL, "nvidia-smi 返回非零：%s" % (out.stderr.strip() or out.stdout.strip()))
        return None
    lines = [ln.strip() for ln in out.stdout.strip().splitlines() if ln.strip()]
    total_gb = None
    for ln in lines:
        parts = [p.strip() for p in ln.split(",")]
        emit(INFO, "GPU: %s | 显存 total/used/free(MB) = %s" % (parts[0], ",".join(parts[1:])))
        try:
            total_gb = float(parts[1]) / 1024.0
        except Exception:
            pass
    emit(PASS, "nvidia-smi 正常。")
    return total_gb


def check_torch():
    try:
        import torch  # type: ignore
    except Exception:
        emit(FAIL, "torch 未安装 -> 装好对应 CUDA 版本的 PyTorch 才能训练。")
        return None
    emit(INFO, "torch %s" % getattr(torch, "__version__", "?"))
    try:
        avail = torch.cuda.is_available()
    except Exception as exc:
        emit(FAIL, "torch.cuda.is_available() 异常：%s" % exc)
        return None
    if not avail:
        emit(FAIL, "torch.cuda.is_available()=False：装了 CPU 版 torch 或驱动不匹配 -> 无法用 GPU。")
        return None
    n = torch.cuda.device_count()
    emit(PASS, "CUDA 可用，设备数=%d" % n)
    total_gb = None
    for i in range(n):
        p = torch.cuda.get_device_properties(i)
        gb = p.total_memory / (1024 ** 3)
        if i == 0:
            total_gb = gb
        emit(INFO, "  cuda:%d %s  显存=%.1fGB  支持 bf16=%s fp16=%s"
             % (i, p.name, gb, getattr(p, "supports_bfloat16", "?"), "yes"))
    return total_gb


def check_models(models_dir):
    md = Path(models_dir)
    if not md.exists():
        emit(FAIL, "models/ 目录不存在：%s" % md)
        return
    files = [Path(x) for x in glob.glob(str(md / "**" / "*.*"), recursive=True)
             if Path(x).suffix.lower() in (".safetensors", ".ckpt", ".pth", ".pt", ".bin", ".pkl")]
    if not files:
        emit(FAIL, "models/ 内未发现任何权重文件（SPEC §0.9：SDXL base 由你自备放入，骨架里 models/ 是空的）。")
        return
    names = [f.name.lower() for f in files]
    sdxl = [f.name for f, nl in zip(files, names) if ("sd_xl" in nl or "sdxl" in nl or "sd-xl" in nl)]
    vae = [f.name for f, nl in zip(files, names) if "vae" in nl]
    flux = [f.name for f, nl in zip(files, names) if "flux" in nl]
    emit(INFO, "models/ 权重 %d 个。" % len(files))
    if sdxl:
        emit(PASS, "疑似 SDXL base：%s" % ", ".join(sdxl[:4]))
    else:
        emit(FAIL, "未见 SDXL base 权重（名字含 sd_xl/sdxl）-> SDXL LoRA 训练缺底模。")
    if vae:
        emit(INFO, "含 VAE：%s" % ", ".join(vae[:3]))
    if flux:
        emit(WARN, "检测到 FLUX 权重：%s（8GB 默认禁用 FLUX，见 SPEC §8.2 disallow_default）。" % ", ".join(flux[:3]))


def _guess_sd_scripts(arg):
    if arg:
        return [arg]
    here = Path.cwd()
    cands = [
        os.environ.get("SD_SCRIPTS_DIR"),
        str(ROOT / "sd-scripts"),
        str(ROOT.parent / "sd-scripts"),
        str(here / "sd-scripts"),
        str(here.parent / "sd-scripts"),
    ]
    return [c for c in cands if c]


def check_kohya(sd_scripts_arg):
    entry_names = ("sdxl_train_network.py", "train_network.py")
    for base in _guess_sd_scripts(sd_scripts_arg):
        b = Path(base)
        hits = [str(b / e) for e in entry_names if (b / e).exists()]
        if not hits and b.exists():
            hits = glob.glob(str(b / "**" / "sdxl_train_network.py"), recursive=True)
        if hits:
            emit(PASS, "kohya sd-scripts 入口：%s" % hits[0])
            lib = b / "library"
            if lib.exists():
                emit(PASS, "kohya library/ 就位。")
            else:
                emit(WARN, "kohya 入口在但未见 library/，确认完整检出。")
            return True
    emit(FAIL, "未发现 kohya sd-scripts（可 --sd-scripts 指定路径，或 git clone sd-scripts 并 pip install -r requirements）。")
    return False


def check_skeleton():
    need = ["schema/caption.schema.json", "hardware/8gb.yaml", "prompts/generate_en.yaml",
            "data/provenance.csv", "scripts/make_kohya_structure.py", "scripts/caption_lint.py",
            "scripts/license_gate.py"]
    missing = [p for p in need if not (ROOT / p).exists()]
    if missing:
        emit(WARN, "仓库骨架缺：%s（跑 python scripts/init_tree.py 或等本工具补脚本）。" % ", ".join(missing))
    else:
        emit(PASS, "仓库骨架与冒烟脚本齐备。")


def check_disk():
    try:
        du = shutil.disk_usage(str(ROOT))
        free_gb = du.free / (1024 ** 3)
        emit(PASS if free_gb > 20 else WARN, "磁盘剩余 %.1fGB（SDXL 权重/latents 缓存需较多空间）。" % free_gb)
    except Exception as exc:
        emit(INFO, "磁盘检查跳过：%s" % exc)


def main():
    ap = argparse.ArgumentParser(description="decomineral GPU 训练机体检")
    ap.add_argument("--sd-scripts", default=None, help="kohya sd-scripts 目录")
    ap.add_argument("--models", default=str(ROOT / "models"), help="权重目录")
    args = ap.parse_args()

    print("== decomineral env_check ==")
    check_python()
    smi_gb = check_nvidia_smi()
    torch_gb = check_torch()
    total_gb = torch_gb if torch_gb is not None else smi_gb
    profile, why = vram_to_profile(total_gb)
    print("-" * 60)
    emit(INFO, "剖面建议：%s（%s）" % (profile or "?", why))
    check_models(args.models)
    check_kohya(args.sd_scripts)
    check_skeleton()
    check_disk()

    print("-" * 60)
    blockers = []
    if _state.get(FAIL, 0):
        # 汇总 FAIL 行已由上方逐条打印
        blockers = [FAIL]
    verdict = "NO-GO" if FAIL in _state else "GO"
    print("结果：PASS=%d WARN=%d FAIL=%d  ->  今晚冒烟判定：%s"
          % (_state.get(PASS, 0), _state.get(WARN, 0), _state.get(FAIL, 0), verdict))
    if verdict == "NO-GO":
        print("上面所有 [FAIL] 就是今晚的阻塞项；逐条清掉后重跑本脚本变 GO，再进 license_gate -> caption_lint -> make_kohya_structure。")
    else:
        print("环境 OK。下一步：准备 4-8 张 PD/CC0 图入 data/inbox/raw 并写 provenance，跑 license_gate/caption_lint，再用 make_kohya_structure 打印训练命令。")
    sys.exit(0 if verdict == "GO" else 2)


if __name__ == "__main__":
    main()
