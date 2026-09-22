#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_commons.py — Wikimedia Commons 候选抓取（SPEC §10 第 4 步；§2.4 白名单）。

逐文件核许可（§11：**分类本身不是许可**，必须读文件页 extmetadata）。只收 LicenseShortName
为 Public domain / CC0 者；其余跳过。保存 file page url 与 meta.json 到 inbox/raw。
仅用标准库；礼貌限速。Commons 混有现代游客摄影（许可属拍摄者，不是壁画的）——本工具只按
LicenseShortName 粗筛 PD/CC0，**卒年/出版年证据仍须 license_gate + 人工核原页**（§2.1）。

用法：
    python scripts/fetch_commons.py --category "Category:Persian miniatures" --limit 8
    python scripts/fetch_commons.py --category "Category:Mogao Cave paintings" --limit 6
"""

import argparse
import hashlib
import json
import re
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
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia 机器人政策要求「带联系方式的描述性 UA」，否则易 403。同时加 Accept。
UA = {
    "User-Agent": "decomineral-lora/1.0 (https://commons.wikimedia.org; non-commercial public-domain art dataset research; python-urllib)",
    "Accept": "application/json",
}
THUMB_WIDTH = 2048
OK_HINTS = ("public domain", "cc0", "cc zero", "pd-old", "pd art")


def http_json(url, tries=4):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code in (403, 429, 500, 502, 503, 504):
                time.sleep(5 * (2 ** i))  # 指数退避 5/10/20/40s
                continue
            raise
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(3 * (i + 1))
    raise last


def download(url, dest, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r, open(dest, "wb") as f:
                f.write(r.read())
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(3 * (2 ** i))
    raise last


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


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def norm_license(lic_short):
    low = (lic_short or "").lower()
    if "public domain" in low or low.startswith("pd"):
        return "PD"
    if "cc0" in low or "cc zero" in low:
        return "CC0"
    return lic_short or ""


def license_ok(lic_short):
    low = (lic_short or "").lower()
    return any(h in low for h in OK_HINTS)


def category_files(category, limit):
    params = {
        "action": "query", "generator": "categorymembers", "gcmtitle": category,
        "gcmtype": "file", "gcmlimit": str(limit), "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime", "iiurlwidth": str(THUMB_WIDTH),
        "format": "json", "formatversion": "2",
    }
    data = http_json(COMMONS_API + "?" + urllib.parse.urlencode(params))
    return (data.get("query", {}) or {}).get("pages", []) or []


def search_files(term, limit):
    """Commons 全文检索（generator=search, ns=6 文件页，§2.4 白名单）。"""
    params = {
        "action": "query", "generator": "search", "gsrsearch": term,
        "gsrnamespace": "6", "gsrlimit": str(limit), "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime", "iiurlwidth": str(THUMB_WIDTH),
        "format": "json", "formatversion": "2",
    }
    data = http_json(COMMONS_API + "?" + urllib.parse.urlencode(params))
    return (data.get("query", {}) or {}).get("pages", []) or []


def subcategories_of(category, limit):
    """一层子分类展开（仍属用户指定 Commons 分类树内，§2.4 白名单）。"""
    params = {
        "action": "query", "list": "categorymembers", "cmtitle": category,
        "cmtype": "subcat", "cmlimit": str(limit), "format": "json", "formatversion": "2",
    }
    data = http_json(COMMONS_API + "?" + urllib.parse.urlencode(params))
    members = (data.get("query", {}) or {}).get("categorymembers", []) or []
    return [m.get("title") for m in members if m.get("title")]


def fetch_one(page, out_root):
    title = page.get("title", "File")
    ii = (page.get("imageinfo") or [{}])[0]
    mime = (ii.get("mime") or "").lower()
    if not mime.startswith("image/"):
        return None, "非图像文件（mime=%s，如 PDF）" % (mime or "?")
    em = ii.get("extmetadata", {}) or {}
    lic_short = strip_html((em.get("LicenseShortName", {}) or {}).get("value", ""))
    if not license_ok(lic_short):
        return None, "许可非 PD/CC0（%s）" % (lic_short or "未知")
    img_url = ii.get("thumburl") or ii.get("url")
    page_url = ii.get("descriptionurl", "")
    if not img_url:
        return None, "无图像 URL"
    fid = "commons_" + re.sub(r"[^A-Za-z0-9]+", "_", title.replace("File:", ""))[:60].strip("_")
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
        "source": "commons",
        "institution": "Wikimedia Commons",
        "page_url": page_url,
        "direct_url": img_url,
        "license": norm_license(lic_short),
        "license_url": strip_html((em.get("LicenseUrl", {}) or {}).get("value", "")),
        "creator": strip_html((em.get("Artist", {}) or {}).get("value", "")),
        "creator_death_year": "",
        "publication_year": strip_html((em.get("DateTimeOriginal", {}) or {}).get("value", "")),
        "family": "",
        "theme_primary": "",
        "width": w or "",
        "height": h or "",
        "sha256": sha256_of(img_path),
        "title": title,
        "license_short": lic_short,
        "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return fid, title


def main():
    ap = argparse.ArgumentParser(description="decomineral Wikimedia Commons 抓取")
    ap.add_argument("--category", action="append", default=[], help="Commons 分类，可多次")
    ap.add_argument("--search", action="append", default=[],
                    help="Commons 全文检索词（ns=6 文件页），可多次；绕过分类字母序限制")
    ap.add_argument("--limit", type=int, default=6, help="每个分类取前 N 个（默认 6）")
    ap.add_argument("--subcats", type=int, default=0,
                    help="展开一层子分类，最多 N 个（默认 0=不展开）")
    ap.add_argument("--out", default=str(ROOT / "data" / "inbox" / "raw"))
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()

    if not args.category and not args.search:
        ap.error("需要 --category 或 --search 之一")

    total_new = 0
    for term in args.search:
        print("== search: %s ==" % term)
        try:
            pages = search_files(term, args.limit)
        except Exception as exc:
            print("  检索失败：%s" % exc)
            continue
        print("  取到 %d 个文件页" % len(pages))
        for pg in pages:
            try:
                fid, title = fetch_one(pg, args.out)
            except Exception as exc:
                print("  - 抓取失败：%s" % exc)
                continue
            if fid is None:
                print("  - 跳过：%s（%s）" % (pg.get("title", "?")[:40], title))
                continue
            total_new += 1
            print("  - %s  %s" % (fid, (title or "")[:50]))
            time.sleep(args.delay)
        time.sleep(args.delay)
    for cat in args.category:
        worklist = [cat]
        if args.subcats > 0:
            try:
                subs = subcategories_of(cat, args.subcats)
            except Exception as exc:
                subs = []
                print("== %s 子分类查询失败：%s" % (cat, exc))
            if subs:
                print("== %s 展开子分类 %d 个：%s" %
                      (cat, len(subs), "; ".join(s.replace("Category:", "")[:40] for s in subs)))
                worklist += subs
            time.sleep(args.delay)
        for c in worklist:
            print("== category: %s ==" % c)
            try:
                pages = category_files(c, args.limit)
            except Exception as exc:
                print("  查询失败：%s" % exc)
                continue
            print("  取到 %d 个文件页" % len(pages))
            for pg in pages:
                try:
                    fid, title = fetch_one(pg, args.out)
                except Exception as exc:
                    print("  - 抓取失败：%s" % exc)
                    continue
                if fid is None:
                    print("  - 跳过：%s（%s）" % (pg.get("title", "?")[:40], title))
                    continue
                total_new += 1
                print("  - %s  %s" % (fid, (title or "")[:50]))
                time.sleep(args.delay)
            time.sleep(args.delay)
    print("-" * 60)
    print("本轮新增 %d 个候选 -> %s。" % (total_new, args.out))
    print("下一步：python scripts/license_gate.py --inbox data/inbox/raw --csv data/provenance.csv")
    print("提醒：Commons 须逐文件核许可（§11）；这些仅是候选，风格须人工看图（§3.1）。")


if __name__ == "__main__":
    main()
