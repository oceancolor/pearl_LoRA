#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性：汇总 inbox 全部候选 meta 台账。"""
import glob
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

rows = []
for p in sorted(glob.glob("data/inbox/raw/*/meta.json")):
    m = json.load(open(p, encoding="utf-8"))
    rows.append((
        m["file_id"],
        "%sx%s" % (m.get("width"), m.get("height")),
        str(m.get("license_short") or m.get("license"))[:16],
        (m.get("creator") or "")[:24],
        (m.get("publication_year") or "")[:28],
        (m.get("title") or "")[:48],
    ))
print("%-56s %-11s %-16s %-24s %-28s %s" % ("file_id", "WxH", "license", "creator", "date", "title"))
print("-" * 150)
for r in rows:
    print("%-56s %-11s %-16s %-24s %-28s %s" % r)
print("共 %d 条" % len(rows))
