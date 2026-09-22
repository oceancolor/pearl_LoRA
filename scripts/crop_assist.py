#!/usr/bin/env python3
"""crop_assist.py — SPEC §10 第 7 步：人工裁切辅助（自动去边仅作建议）。

从 data/inbox/raw/<file_id>/ 读取原图，按「四角背景色距离 + 行列方差」
自动估算内容边界框，把建议裁切写入 data/crops/<file_id>.png，
并输出 data/crops/_proposals.json 供人工逐张确认。

铁律（与仓库其它脚本一致）：
- 自动裁切只是建议，正式入册（train/images 三件套）前必须人工看图确认；
- 只处理 provenance.csv 中 decision=train 且已目检（family 非空）的行；
- 不改写原图，不写 provenance（确认后由人工/后续脚本回填 train_filename）。

用法：
  python scripts/crop_assist.py                      # 所有已目检未入册的行
  python scripts/crop_assist.py --ids met_44794 ...  # 指定候选
  python scripts/crop_assist.py --tol 24 --pad 8     # 调整容差/回缩边距
  python scripts/crop_assist.py --ids met_44794 --bbox met_44794:120,300,1900,3800
                                                     # 手动指定原图坐标框（可多个），
                                                     # 跳过自动估算且不再回缩 pad
依赖：Pillow（缺失时打印 NO-GO 退出）。
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "provenance.csv"
RAW_DIR = ROOT / "data" / "inbox" / "raw"
CROPS_DIR = ROOT / "data" / "crops"

IMG_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".webp")


def find_original(file_id: str) -> Path | None:
    d = RAW_DIR / file_id
    if not d.is_dir():
        return None
    for p in sorted(d.iterdir()):
        if p.suffix.lower() in IMG_EXTS:
            return p
    return None


def corner_color(im, patch: int = 16):
    """四角小块中位色，作为背景色估计。"""
    w, h = im.size
    g = im.convert("L")
    px = g.load()
    pts = []
    for cx in (0, w - patch):
        for cy in (0, h - patch):
            vals = [px[cx + i, cy + j] for i in range(patch) for j in range(patch)]
            vals.sort()
            pts.append(vals[len(vals) // 2])
    pts.sort()
    return pts[len(pts) // 2]


def content_bbox(im, tol: int, frac: float):
    """扫描出内容边界框：行/列中与背景色差 > tol 的像素占比 >= frac 视为内容。"""
    g = im.convert("L")
    w, h = im.size
    bg = corner_color(g)
    small = g.resize((min(w, 800), max(1, round(h * min(w, 800) / w))))
    sw, sh = small.size
    px = small.load()

    def row_content(y):
        n = sum(1 for x in range(0, sw, 2) if abs(px[x, y] - bg) > tol)
        return n / (sw / 2) >= frac

    def col_content(x):
        n = sum(1 for y in range(0, sh, 2) if abs(px[x, y] - bg) > tol)
        return n / (sh / 2) >= frac

    top = next((y for y in range(sh) if row_content(y)), 0)
    bot = next((y for y in range(sh - 1, -1, -1) if row_content(y)), sh - 1)
    left = next((x for x in range(sw) if col_content(x)), 0)
    right = next((x for x in range(sw - 1, -1, -1) if col_content(x)), sw - 1)

    sx, sy = w / sw, h / sh
    return (
        max(0, int(left * sx)),
        max(0, int(top * sy)),
        min(w, int((right + 1) * sx)),
        min(h, int((bot + 1) * sy)),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="裁切辅助：自动去边建议（SPEC §10 第 7 步）")
    ap.add_argument("--ids", nargs="*", default=None, help="指定 file_id；缺省=已目检未入册全部")
    ap.add_argument("--tol", type=int, default=20, help="背景色差容差（默认 20）")
    ap.add_argument("--frac", type=float, default=0.02, help="行/列内容像素占比阈值（默认 0.02）")
    ap.add_argument("--pad", type=int, default=4, help="边界框向内回缩像素（默认 4）")
    ap.add_argument("--bbox", nargs="*", default=None,
                    help="手动覆盖框 file_id:l,t,r,b（原图像素坐标，可多个）；跳过自动估算与 pad")
    ap.add_argument("--out", type=Path, default=CROPS_DIR)
    args = ap.parse_args()

    overrides: dict[str, tuple[int, int, int, int]] = {}
    for item in args.bbox or []:
        try:
            fid, nums = item.split(":", 1)
            box = tuple(int(v) for v in nums.split(","))
            if len(box) != 4:
                raise ValueError
            overrides[fid] = box  # type: ignore[assignment]
        except ValueError:
            print(f"WARN: --bbox 格式错误（应 file_id:l,t,r,b）: {item}")

    try:
        from PIL import Image
    except ImportError:
        print("NO-GO: 需要 Pillow（pip install Pillow）")
        return 2

    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if args.ids:
        targets = [r for r in rows if r["file_id"] in set(args.ids)]
        missing = set(args.ids) - {r["file_id"] for r in targets}
        if missing:
            print(f"WARN: provenance 无记录: {sorted(missing)}")
    else:
        targets = [
            r for r in rows
            if r["decision"] == "train" and r["family"].strip() and not r["train_filename"].strip()
        ]

    if not targets:
        print("无待裁切候选（已目检且未入册为空）。")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    proposals = []
    for r in targets:
        fid = r["file_id"]
        src = find_original(fid)
        if not src:
            print(f"SKIP {fid}: inbox/raw 无原图")
            continue
        im = Image.open(src)
        im.load()
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        w, h = im.size
        if fid in overrides:
            l, t, rt, b = overrides[fid]
            l, t = max(0, l), max(0, t)
            rt, b = min(w, rt), min(h, b)
            if rt - l < 2 or b - t < 2:
                print(f"SKIP {fid}: --bbox 框过小 {(l, t, rt, b)}")
                continue
            mode = "manual"
        else:
            l, t, rt, b = content_bbox(im, args.tol, args.frac)
            l, t = min(l + args.pad, rt - 1), min(t + args.pad, b - 1)
            rt, b = max(rt - args.pad, l + 1), max(b - args.pad, t + 1)
            mode = "auto"
        crop = im.crop((l, t, rt, b))
        out = args.out / f"{fid}.png"
        crop.save(out)
        short = min(crop.size)
        proposals.append({
            "file_id": fid,
            "family": r["family"],
            "theme_primary": r["theme_primary"],
            "source": str(src.relative_to(ROOT)),
            "orig_size": [w, h],
            "bbox": [l, t, rt, b],
            "mode": mode,
            "crop_size": list(crop.size),
            "short_side": short,
            "ok_640": short >= 640,
            "out": str(out.relative_to(ROOT)),
        })
        flag = "OK" if short >= 640 else "!! 短边<640"
        print(f"{fid} [{r['family']}/{r['theme_primary']}] {w}x{h} -> {crop.size[0]}x{crop.size[1]}  {flag}  ({mode})")

    pj = args.out / "_proposals.json"
    if pj.exists():
        try:
            old = json.loads(pj.read_text(encoding="utf-8"))
            done = {p["file_id"] for p in proposals}
            proposals = [p for p in old if p.get("file_id") not in done] + proposals
        except (json.JSONDecodeError, OSError):
            pass
    pj.write_text(json.dumps(proposals, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n共 {len(proposals)} 张建议裁切 -> {args.out.relative_to(ROOT)}/；明细见 _proposals.json")
    print("注意：自动裁切仅为建议（SPEC §10-7），入册前请人工逐张确认。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
