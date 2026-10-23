#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_aic.py — Art Institute of Chicago Open Access 候选抓取。

AIC API 免 key；只收 is_public_domain=true（AIC 公有领域图以 CC0 发布）。
图像走 IIIF：/iiif/2/<image_id>/full/<w>,/0/default.jpg；默认取宽 3000（若服务器限制会自动降级）。
落 data/inbox/raw/aic_<id>/（image.jpg + meta.json），仅作候选，风格须人工看图（§3.1）。

用法：
    python scripts/fetch_aic.py --query "Whistler nocturne" --limit 6
    python scripts/fetch_aic.py --ids 12345,6789
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
API = "https://api.artic.edu/api/v1/artworks"
IIIF = "https://www.artic.edu/iiif/2"
UA = {"User-Agent": "decomineral-lora/1.0 (personal, non-commercial; public-domain dataset research)",
      "AIC-User-Agent": "decomineral-lora (personal research)"}
INSTITUTION = "The Art Institute of Chicago"
LICENSE = "CC0"
LICENSE_URL = "https://www.artic.edu/open-access/open-access-images"
FIELDS = "id,title,image_id,date_display,artist_display,is_public_domain,artwork_type_title," \
         "classification_title,medium_display,department_title"

BLOCK3D = ("sculpture", "vessel", "ceramic", "metalwork", "furniture", "glass", "coin",
           "jewelry", "armor", "arms", "photograph", "bowl", "vase", "jar", "netsuke")
WIDTHS = (3000, 2400, 1686, 843)


def http(url, binary=False, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return data if binary else json.loads(data.decode("utf-8"))


def sha256_of(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def img_size(p):
    try:
        from PIL import Image
        with Image.open(p) as im:
            return im.size
    except Exception:
        return (None, None)


def search(q, limit):
    qs = urllib.parse.urlencode({
        "q": q, "limit": str(limit), "fields": FIELDS,
        "query[term][is_public_domain]": "true",
    })
    return http("%s/search?%s" % (API, qs)).get("data", [])


def by_id(oid):
    return http("%s/%d?fields=%s" % (API, int(oid), FIELDS)).get("data")


def save(obj, out_root):
    oid = obj.get("id")
    if not obj.get("is_public_domain"):
        return None, "非公有领域"
    blob = " ".join(str(obj.get(k) or "") for k in
                    ("artwork_type_title", "classification_title", "medium_display")).lower()
    hit = next((b for b in BLOCK3D if b in blob), None)
    if hit:
        return None, "非平面作品（'%s'）" % hit
    if not obj.get("image_id"):
        return None, "无图像"
    fid = "aic_%d" % oid
    d = Path(out_root) / fid
    d.mkdir(parents=True, exist_ok=True)
    p = d / "image.jpg"
    url = ""
    if not p.exists():
        for w in WIDTHS:
            url = "%s/%s/full/%d,/0/default.jpg" % (IIIF, obj["image_id"], w)
            try:
                p.write_bytes(http(url, binary=True, timeout=120))
                break
            except Exception:
                continue
        else:
            return None, "IIIF 下载失败"
    w, h = img_size(p)
    meta = {
        "file_id": fid, "orig_filename": "image.jpg", "train_filename": "",
        "source": "aic", "institution": INSTITUTION,
        "page_url": "https://www.artic.edu/artworks/%d" % oid,
        "direct_url": url, "license": LICENSE, "license_url": LICENSE_URL,
        "creator": (obj.get("artist_display") or "").replace("\n", " "),
        "creator_death_year": "", "publication_year": obj.get("date_display") or "",
        "family": "", "theme_primary": "", "width": w or "", "height": h or "",
        "sha256": sha256_of(p), "title": obj.get("title") or "",
        "department": obj.get("department_title") or "",
        "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return fid, meta["title"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", action="append", default=[])
    ap.add_argument("--ids", default="")
    ap.add_argument("--limit", type=int, default=6)
    ap.add_argument("--out", default=str(ROOT / "data" / "inbox" / "raw"))
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()
    if not args.query and not args.ids:
        ap.error("需要 --query 或 --ids 之一")

    objs = []
    for raw in [x for x in args.ids.split(",") if x.strip()]:
        try:
            objs.append(by_id(raw))
        except Exception as e:
            print("  - %s 元数据失败 %s" % (raw, e))
    for q in args.query:
        print("== query: %s ==" % q)
        try:
            got = search(q, args.limit)
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
            print("  - aic_%s 失败：%s" % (obj.get("id"), e))
            continue
        if fid is None:
            print("  - aic_%s 跳过：%s" % (obj.get("id"), title))
            continue
        new += 1
        print("  - %s  %s" % (fid, (title or "")[:60]))
        time.sleep(args.delay)
    print("-" * 60)
    print("本轮新增 %d 个候选 -> %s" % (new, args.out))


if __name__ == "__main__":
    main()
