#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断 round4：用 categorymembers 探测分类是否存在（file/subcat 计数），2.5s/req。"""
import json
import sys
import time
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

UA = {"User-Agent": "decomineral-lora/1.0 (personal, non-commercial; public-domain dataset research)"}

CANDS = [
    "Category:Kizil grottoes", "Category:Cave of the Painters (Kizil)",
    "Category:Bezeklik murals", "Category:Paintings in the Ajanta Caves",
    "Category:Ajanta Caves", "Category:Copies of Ajanta paintings",
    "Category:Persian miniatures", "Category:Mughal miniatures",
    "Category:Mughal paintings", "Category:Ragamala", "Category:Shahnama",
    "Category:Illuminated manuscripts of the Shahnama",
    "Category:Al-Jazari", "Category:Book of Fixed Stars",
    "Category:Book of Knowledge of Ingenious Mechanical Devices",
    "Category:Rimpa school", "Category:Ogata Kōrin", "Category:Tawaraya Sōtatsu",
    "Category:The Grammar of Ornament", "Category:Ornament prints",
    "Category:Ivan Bilibin", "Category:Harry Clarke",
    "Category:Edmund Dulac", "Category:Léon Bakst",
]
for cat in CANDS:
    try:
        req = urllib.request.Request(
            "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
                "action": "query", "list": "categorymembers", "cmtitle": cat,
                "cmtype": "file|subcat", "cmlimit": "50",
                "format": "json", "formatversion": "2"}), headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
        ms = (d.get("query", {}) or {}).get("categorymembers", []) or []
        nf = sum(1 for m in ms if m.get("ns") == 6)
        ns = sum(1 for m in ms if m.get("ns") == 14)
        subs = [m["title"].replace("Category:", "")[:36] for m in ms if m.get("ns") == 14][:6]
        tag = "存在" if (nf or ns) else "空/不存在"
        print("%-52s %-8s file~%-3d subcat~%-3d %s" % (cat, tag, nf, ns, "; ".join(subs)))
    except Exception as exc:
        print("%-52s ERR %s" % (cat, exc))
    time.sleep(2.5)
