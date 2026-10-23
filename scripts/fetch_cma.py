#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_cma.py — Cleveland Museum of Art Open Access 候选抓取。

为什么用它：Met 的 /search 接口已 410 Gone（官方下线），而 CMA 的 openaccess-api
免 key、可筛 cc0=1 + has_image=1，原图通常 2000–3000px，正好满足 §5.2 的 768 门槛。

只收 share_license_status=CC0；跳过立体/器物类（§2.3）。落 data/inbox/raw/cma_<id>/
（image.jpg + meta.json），仅作候选，风格须人工看图（§3.1）。

用法：
    python scripts/fetch_cma.py --query "bodhisattva" --query "paradise" --limit 6
    python scripts/fetch_cma.py --ids 12345,6789
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
API = "https://openaccess-api.clevelandart.org/api/artworks"
UA = {"User-Agent": "decomineral-lora/1.0 (personal, non-commercial; public-domain dataset research)"}
INSTITUTION = "The Cleveland Museum of Art"
LICENSE = "CC0"
LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"

# §2.3：拒雕塑/器物/立体物。命中 type/technique/culture 中任一即跳过
BLOCK3D = ("sculpture", "statue", "stele", "stela", "bust", "vessel", "bowl", "vase",
           "ewer", "basin", "jar", "coin", "jewelry", "metalwork", "glass", "tile",
           "armor", "sword", "dagger", "helm", "furniture", "ceramic", "porcelain",
           "bronze", "ivory", "lacquer", "basket", "fan", "mirror", "rug", "carpet")

# 只保留平面作品（§1）
WANT = ("painting", "folio", "album leaf", "album page", "manuscript", "drawing",
        "screen", "textile", "hanging scroll", "handscroll", "woodblock print",
        "print", "illumination", "panel", "leaf")


def http_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        f.write(r.read())


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def img_size(path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return (None, None)


def search(query, limit, department=None, type_=None):
    # 不加部门限定会大量命中西方作品（Blake / 亚当夏娃等），与本项目装饰风格无关
    params = {"q": query, "cc0": "1", "has_image": "1",
              "limit": str(limit), "skip": "0"}
    if department:
        params["department"] = department
    if type_:
        params["type"] = type_
    qs = urllib.parse.urlencode(params)
    return http_json("%s?%s" % (API, qs)).get("data", [])


def by_id(oid):
    return http_json("%s/%d" % (API, int(oid))).get("data")


def save(obj, out_root):
    oid = obj.get("id")
    blob = " ".join(str(obj.get(k, "") or "") for k in ("type", "technique", "culture")).lower()
    if not any(w in blob for w in WANT):
        return None, "非平面作品（type/technique=%s）" % (obj.get("type") or "?")
    hit = next((b for b in BLOCK3D if b in blob), None)
    if hit:
        return None, "命中 3D/器物词 '%s'" % hit
    imgs = obj.get("images") or {}
    # web 只有 ~900px（多半过不了 768 门槛），full 有时 200–350MB 会拖死下载。
    # 故优先 print（约 3000px），其次 full，最后 web。
    img = next((imgs[k] for k in ("print", "full", "web") if imgs.get(k) and imgs[k].get("url")), None)
    if not img:
        return None, "无图像"
    fid = "cma_%d" % oid
    d = Path(out_root) / fid
    d.mkdir(parents=True, exist_ok=True)
    p = d / "image.jpg"
    want_w = int(img.get("width") or 0)
    have_w = img_size(p)[0] if p.exists() else None
    need = (not p.exists()) or (want_w and have_w and have_w < want_w)
    # 已达 768 就不必重下（避免为几十 MB 的 full 版白等）
    if need and have_w and have_w >= 768 and want_w > have_w * 3:
        need = False
    if need:
        download(img["url"], p)
    w, h = img_size(p)
    meta = {
        "file_id": fid, "orig_filename": "image.jpg", "train_filename": "",
        "source": "cma", "institution": INSTITUTION,
        "page_url": (obj.get("url") or "").strip(),
        "direct_url": img["url"], "license": LICENSE, "license_url": LICENSE_URL,
        "creator": ((obj.get("creators") or [{}])[0].get("description") or "") if obj.get("creators") else "",
        "creator_death_year": "", "publication_year": obj.get("creation_date") or "",
        "family": "", "theme_primary": "", "width": w or "", "height": h or "",
        "sha256": sha256_of(p), "title": obj.get("title") or "",
        "department": obj.get("department") or "",
        "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return fid, meta["title"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", action="append", default=[])
    ap.add_argument("--ids", default="")
    ap.add_argument("--limit", type=int, default=6)
    ap.add_argument("--department", default=None,
                    help="CMA 部门，如 'Islamic Art' / 'Japanese and Korean Art' / 'Chinese Art'")
    ap.add_argument("--type", dest="type_", default=None, help="CMA 类型，如 Painting / Print")
    ap.add_argument("--out", default=str(ROOT / "data" / "inbox" / "raw"))
    ap.add_argument("--delay", type=float, default=0.8)
    args = ap.parse_args()

    if not args.query and not args.ids:
        ap.error("需要 --query 或 --ids 之一")

    objs = []
    if args.ids:
        for raw in [x for x in args.ids.split(",") if x.strip()]:
            try:
                objs.append(by_id(raw))
            except Exception as e:
                print("  - %s 取元数据失败 %s" % (raw, e))
    for q in args.query:
        print("== query: %s ==" % q)
        try:
            got = search(q, args.limit, args.department, args.type_)
        except Exception as e:
            print("  搜索失败：%s" % e)
            continue
        print("  命中 %d 个" % len(got))
        objs.extend(got)

    new = 0
    for obj in objs:
        if not obj:
            continue
        try:
            fid, title = save(obj, args.out)
        except Exception as e:
            print("  - cma_%s 失败：%s" % (obj.get("id"), e))
            continue
        if fid is None:
            print("  - cma_%s 跳过：%s" % (obj.get("id"), title))
            continue
        new += 1
        print("  - %s  %s" % (fid, (title or "")[:60]))
        time.sleep(args.delay)

    print("-" * 60)
    print("本轮新增 %d 个候选 -> %s" % (new, args.out))
    print("下一步：python scripts/_ct.py  看尺寸；目检后再 python scripts/build_concept_set.py")


if __name__ == "__main__":
    main()
