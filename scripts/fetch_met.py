#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_met.py — The Met Open Access 候选抓取（SPEC §10 第 3 步；§2.4 白名单）。

只收 isPublicDomain=true（Met 开放获取 = CC0）。下载原图 + 写 meta.json 到
data/inbox/raw/met_<objectID>/，供 license_gate 汇总进 provenance。
注意：只进 inbox/raw 候选；风格是否合 §3.1 由人工看图决定，**不自动当 train**（§10/§3.1）。
仅用标准库。礼貌限速（§5.1：Met 官方 ~80 req/s，本工具实跑 1–2 req/s）。

用法：
    python scripts/fetch_met.py --query "Shahnama miniature" --limit 8
    python scripts/fetch_met.py --query "Persian miniature" --query "illuminated manuscript" --limit 6
"""

import argparse
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
API = "https://collectionapi.metmuseum.org/public/collection/v1"
UA = {"User-Agent": "decomineral-lora/1.0 (personal, non-commercial; public-domain dataset research)"}
LICENSE = "CC0"
LICENSE_URL = "https://www.metmuseum.org/about-the-met/policies-and-documents/open-access"
INSTITUTION = "The Metropolitan Museum of Art"

# 平面作品门（§1 要平面作品；§2.3 拒雕塑/建筑/立体物/照片级三维文物）。
# 命中 objectName/classification/medium 中任一 3D 词即跳过。textile/costume 不在列（属 F 纯图案/织物）。
BLOCK3D = ("sculpture", "statue", "stela", "stele", "bust", "marble", "bronze", "ceramic",
           "vessel", "bowl", "vase", "ewer", "basin", "furniture", "armor", "sword", "dagger",
           "coin", "jewelry", "metalwork", "glass", "tile", "wood", "ivory", "jade", "relief",
           "cameo", "seal", "lamp", "helmet", "gun", "clock", "watch", "figure", "figurine",
           "architectural", "building")


def http_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r, open(dest, "wb") as f:
        f.write(r.read())


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def img_size(path):
    try:
        from PIL import Image  # type: ignore
        with Image.open(path) as im:
            return im.size
    except Exception:
        return (None, None)


def search_ids(query, limit, department_id=None):
    params = {"q": query, "hasImages": "true", "isPublicDomain": "true"}
    if department_id:
        params["departmentId"] = str(department_id)
    qs = urllib.parse.urlencode(params)
    data = http_json("%s/search?%s" % (API, qs))
    ids = data.get("objectIDs") or []
    return ids[:limit]


def fetch_one(oid, out_root):
    obj = http_json("%s/objects/%d" % (API, oid))
    if not obj.get("isPublicDomain"):
        return None, "非 PublicDomain"
    blob = " ".join(str(obj.get(k, "") or "") for k in
                    ("objectName", "classification", "medium", "department")).lower()
    hit = next((b for b in BLOCK3D if b in blob), None)
    if hit:
        return None, "非平面作品（命中 3D 词 '%s'，§2.3）" % hit
    img_url = obj.get("primaryImage") or obj.get("primaryImageSmall")
    if not img_url:
        return None, "无图像"
    fid = "met_%d" % oid
    d = Path(out_root) / fid
    d.mkdir(parents=True, exist_ok=True)
    ext = ".jpg"
    for e in (".png", ".jpg", ".jpeg"):
        if img_url.lower().split("?")[0].endswith(e):
            ext = e
    img_path = d / ("image" + ext)
    if not img_path.exists():
        download(img_url, img_path)
    w, h = img_size(img_path)
    meta = {
        "file_id": fid,
        "orig_filename": img_path.name,
        "train_filename": "",
        "source": "met",
        "institution": INSTITUTION,
        "page_url": obj.get("objectURL", ""),
        "direct_url": img_url,
        "license": LICENSE,
        "license_url": LICENSE_URL,
        "creator": obj.get("artistDisplayName", "") or "",
        "creator_death_year": "",
        "publication_year": obj.get("objectDate", "") or "",
        "family": "",
        "theme_primary": "",
        "width": w or "",
        "height": h or "",
        "sha256": sha256_of(img_path),
        "title": obj.get("title", ""),
        "department": obj.get("department", ""),
        "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return fid, obj.get("title", "")


def main():
    ap = argparse.ArgumentParser(description="decomineral Met Open Access 抓取")
    ap.add_argument("--query", action="append", default=[], help="检索词，可多次")
    ap.add_argument("--ids", default="",
                    help="按 objectID 直接抓取，逗号分隔（配合 _probe_met.py 探查后精取；此时可不给 --query）")
    ap.add_argument("--limit", type=int, default=6, help="每个 query 取前 N 个（默认 6）")
    ap.add_argument("--out", default=str(ROOT / "data" / "inbox" / "raw"))
    ap.add_argument("--delay", type=float, default=1.0, help="对象抓取间隔秒（默认 1）")
    ap.add_argument("--department-id", type=int, default=None,
                    help="限定 Met 部门（6=Asian Art；自由文本对壁画/琳派不靠谱时用）")
    args = ap.parse_args()

    if not args.query and not args.ids:
        ap.error("需要 --query 或 --ids 之一")

    total_new = 0
    if args.ids:
        for raw in [x for x in args.ids.split(",") if x.strip()]:
            oid = int(raw)
            try:
                fid, title = fetch_one(oid, args.out)
            except Exception as exc:
                print("  - met_%d 抓取失败：%s" % (oid, exc))
                continue
            if fid is None:
                print("  - met_%d 跳过：%s" % (oid, title))
                continue
            total_new += 1
            print("  - %s  %s" % (fid, (title or "")[:60]))
            time.sleep(args.delay)
        print("-" * 60)
        print("本轮新增 %d 个候选 -> %s。" % (total_new, args.out))
        return

    for q in args.query:
        print("== query: %s ==" % q)
        try:
            ids = search_ids(q, args.limit, args.department_id)
        except Exception as exc:
            print("  搜索失败：%s" % exc)
            continue
        print("  命中 %d 个（取前 %d）" % (len(ids), min(len(ids), args.limit)))
        for oid in ids:
            try:
                fid, title = fetch_one(oid, args.out)
            except Exception as exc:
                print("  - met_%d 抓取失败：%s" % (oid, exc))
                continue
            if fid is None:
                print("  - met_%d 跳过：%s" % (oid, title))
                continue
            total_new += 1
            print("  - %s  %s" % (fid, (title or "")[:60]))
            time.sleep(args.delay)
    print("-" * 60)
    print("本轮新增 %d 个候选 -> %s（各含 meta.json + 原图）。" % (total_new, args.out))
    print("下一步：python scripts/license_gate.py --inbox data/inbox/raw --csv data/provenance.csv")
    print("提醒：仅为候选。风格须人工看图（§3.1）；进 train/images 前需裁切+caption（§5.3/§6）。")


if __name__ == "__main__":
    main()
