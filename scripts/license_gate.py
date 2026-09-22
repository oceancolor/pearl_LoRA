#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""license_gate.py — 许可/法律闸门（SPEC §10 第 2 步；底线见 §0 / §2）。

职责：判定每张候选图 decision ∈ train|review|reject，写/校验 data/provenance.csv。
铁律：只有 license ∈ {PD, CC0} 且时间/来源合规，才允许 decision=train。非 PD/CC0 一律不 train。

两种用法：
  A) 校验既有 csv（冒烟用）：逐行核 license/时间，把不合规的从 train 降级，并汇总。
       python scripts/license_gate.py --csv data/provenance.csv
  B) 从 inbox/raw 的元数据 JSON 生成行（正式，配合 fetch_*）：
       python scripts/license_gate.py --inbox data/inbox/raw --csv data/provenance.csv
"""

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]

# 允许训练（SPEC §2.1）
TRAIN_OK = {"PD", "CC0"}
# 进复核队列（SPEC §2.2）默认不训练
REVIEW = {"CC-BY", "CC-BY-SA", "CC0-PD?", "NO KNOWN RESTRICTIONS", "NO_KNOWN_RESTRICTIONS"}
# 命中即拒（SPEC §2.3 关键片段，粗筛；最终以人工核原页为准）
REJECT_HINTS = ["nc", "nd", "no derivatives", "all rights reserved", "copyrighted", "edunhuang", "e-dunhuang"]
LIVING_CUTOFF_DEATH = 1955   # 作者卒年 <= 1955（2026 按 life+70）
US_PUB_CUTOFF = 1930         # 或美国出版年 <= 1930
KAY_NIELSEN_UNTIL = "2028-01-01"

# 博物馆开放获取项目（机构已明确 CC0/PD 捐献，§2.1 照片权：开放影像明确 CC0/PD 即可，
# 无需另证卒年）。Commons **不在**此列（混现代摄影，许可属拍摄者，仍走卒年/出版年校验）。
OPEN_ACCESS_SOURCES = {"met", "the metropolitan museum of art", "cleveland museum of art",
                       "cleveland", "smithsonian", "rijksmuseum", "getty",
                       "national museum of asian art", "freer", "sackler"}


def _is_open_access(source, institution):
    blob = " ".join(filter(None, [source, institution])).lower()
    return any(s in blob for s in OPEN_ACCESS_SOURCES)


def _to_int(x):
    try:
        return int(str(x).strip())
    except Exception:
        return None


def classify(license_, death_year, pub_year, creator, source, institution):
    """返回 (decision, reason)。"""
    lic = (license_ or "").strip().upper()
    blob = " ".join(filter(None, [creator, source, institution])).lower()

    for k in ("kay nielsen",):
        if k in blob:
            return "review", "Kay Nielsen 卒于1957，life+70到2028；%s 前禁止训练（SPEC §2.3）。" % KAY_NIELSEN_UNTIL
    for hint in REJECT_HINTS:
        if hint in lic.lower():
            return "reject", "许可含受限片段 '%s'（NC/ND/ARR/敦煌等）→ 拒绝（§2.3）。" % hint
    if lic in TRAIN_OK:
        d = _to_int(death_year)
        p = _to_int(pub_year)
        if d is not None and d > LIVING_CUTOFF_DEATH:
            return "review", "卒年 %d>1955，可能仍在版权内，人工核（§2.1/§2.3）。" % d
        if _is_open_access(source, institution):
            return "train", "license=%s 且来自开放获取机构（%s，明确 CC0/PD，§2.1 照片权）；可 train。" % (lic, (institution or source))
        time_ok = (d is not None and d <= LIVING_CUTOFF_DEATH) or (p is not None and p <= US_PUB_CUTOFF)
        if not time_ok:
            return "review", "PD/CC0 但缺卒年/出版年，补时间证据再 train（§2.1）。"
        return "train", "license=%s 且时间合规；可 train。" % lic
    if lic in REVIEW:
        return "review", "license=%s 属复核队列，默认不训练（§2.2）。" % lic
    return "review", "license=%s 非 PD/CC0，须人工到原页核实（§0.3/§2.1）。" % (lic or "空")


FIELDS = ["file_id", "orig_filename", "train_filename", "source", "institution", "page_url",
          "direct_url", "license", "license_url", "creator", "creator_death_year",
          "publication_year", "family", "theme_primary", "width", "height", "sha256",
          "decision", "decision_reason", "downloaded_at"]


def validate_csv(csv_path):
    p = Path(csv_path)
    if not p.exists():
        print("provenance.csv 不存在：%s" % p)
        return 1
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    if not rows:
        print("provenance.csv 只有表头，无记录（还没下载/登记候选）。")
        return 0
    counts = {"train": 0, "review": 0, "reject": 0}
    changed = []
    for r in rows:
        dec, reason = classify(r.get("license"), r.get("creator_death_year"),
                               r.get("publication_year"), r.get("creator"),
                               r.get("source"), r.get("institution"))
        cur = (r.get("decision") or "").strip().lower()
        counts[cur] = counts.get(cur, 0) + 1
        if cur == "train" and dec != "train":
            changed.append((r.get("file_id"), r.get("train_filename"), reason))
        print("  %-10s lic=%-16s 判定=%-6s %s" % (r.get("file_id"), r.get("license") or "?", dec, reason))
    print("-" * 60)
    print("当前 decision 统计：%s" % counts)
    if changed:
        print("!! %d 张被标 train 但未过门，须改回 review/reject（§0.3/§2）：" % len(changed))
        for fid, tf, reason in changed:
            print("   - %s (%s): %s" % (fid, tf, reason))
        return 3
    train_n = counts.get("train", 0)
    print("gate 通过：train=%d。冒烟只需 >=4；正式最小实验需 >=36 且 theme 配额（§9/§3.3）。" % train_n)
    if train_n < 36:
        print("（提醒：不足 36 张或配额未达 -> 满足的是“冒烟”，不是 §9 最小实验。）")
    return 0


def build_from_inbox(inbox_dir, csv_path):
    """从 inbox/raw/<file_id>/meta.json 生成/更新 provenance 行。meta.json 需含来源与许可字段。"""
    inbox = Path(inbox_dir)
    existing = {}
    if Path(csv_path).exists():
        for r in csv.DictReader(open(csv_path, encoding="utf-8")):
            existing[r["file_id"]] = r
    added, seen = 0, set()
    kept = 0  # 人工判定被保留的行数
    for sub in sorted(p for p in inbox.glob("*") if p.is_dir()):
        meta = sub / "meta.json"
        if not meta.exists():
            continue
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
        except Exception as exc:
            print("  跳过 %s：meta.json 解析失败 %s" % (sub.name, exc))
            continue
        fid = m.get("file_id", sub.name)
        lic = m.get("license", "")
        dec, reason = classify(lic, m.get("creator_death_year"), m.get("publication_year"),
                               m.get("creator"), m.get("source"), m.get("institution"))
        row = {k: m.get(k, "") for k in FIELDS}
        row.update({"file_id": fid, "orig_filename": m.get("orig_filename", sub.name),
                    "train_filename": m.get("train_filename", ""), "source": m.get("source", ""),
                    "institution": m.get("institution", ""), "page_url": m.get("page_url", ""),
                    "direct_url": m.get("direct_url", ""), "license": lic,
                    "license_url": m.get("license_url", ""), "creator": m.get("creator", ""),
                    "creator_death_year": m.get("creator_death_year", ""),
                    "publication_year": m.get("publication_year", ""),
                    "family": m.get("family", ""), "theme_primary": m.get("theme_primary", ""),
                    "width": m.get("width", ""), "height": m.get("height", ""),
                    "sha256": m.get("sha256", ""), "decision": dec, "decision_reason": reason,
                    "downloaded_at": m.get("downloaded_at", datetime.now(timezone.utc).isoformat())})
        prev = existing.get(fid)
        if prev:
            # 人工策展字段粘性保留（§0.3：人工判定优先于自动分类，meta.json 只供事实字段）。
            # train_filename/family/theme_primary/creator/creator_death_year/publication_year
            # 由人工目检补证（triage），一律保留；
            # decision/decision_reason 仅在许可仍允许训练时保留（许可变差则回落自动判定）。
            for k in ("train_filename", "family", "theme_primary",
                      "creator", "creator_death_year", "publication_year"):
                if (prev.get(k) or "").strip():
                    row[k] = prev[k]
            if (prev.get("decision") or "").strip() and \
               (lic.strip().upper() in TRAIN_OK or prev.get("decision") != "train"):
                row["decision"] = prev["decision"]
                row["decision_reason"] = prev.get("decision_reason") or reason
                kept += 1
        existing[fid] = row
        seen.add(fid)
        added += 1
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for fid in sorted(existing):
            w.writerow({k: existing[fid].get(k, "") for k in FIELDS})
    print("从 inbox 生成/更新 provenance：本轮纳入 %d 条，总 %d 条（保留人工判定 %d 行）。" % (added, len(existing), kept))
    return 0


def main():
    ap = argparse.ArgumentParser(description="decomineral 许可闸门")
    ap.add_argument("--csv", default=str(ROOT / "data/provenance.csv"))
    ap.add_argument("--inbox", default=None, help="data/inbox/raw，提供则从 meta.json 生成行")
    args = ap.parse_args()
    if args.inbox:
        sys.exit(build_from_inbox(args.inbox, args.csv))
    sys.exit(validate_csv(args.csv))


if __name__ == "__main__":
    main()
