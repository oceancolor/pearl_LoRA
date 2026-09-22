"""_probe_met.py — Met 候选「只探查不下载」triage（§2.4 白名单 API，1 req/s）。

fetch_met.py 会直接下原图，命中的大量欧洲油画/陶瓷既占盘又没用；
本脚本只打 search + objects 接口，打印 id / title / objectName / classification / medium，
由人挑选后把 objectID 交给 `fetch_met.py --ids ...` 正式抓。

用法：
  python scripts/_probe_met.py --query "waves" --department-id 6 --limit 10
  python scripts/_probe_met.py --query pool --query garden --department-id 14
  python scripts/_probe_met.py --ids 448959,453385
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request

API = "https://collectionapi.metmuseum.org/public/collection/v1"
UA = {"User-Agent": "decomineral-lora/1.0 (personal, non-commercial; public-domain dataset research)"}

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def http_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def brief(obj):
    return "%s | %s | %s | %s | %s" % (
        obj.get("objectID"),
        (obj.get("title") or "")[:46],
        (obj.get("objectName") or "")[:26],
        (obj.get("classification") or "")[:22],
        (obj.get("medium") or "")[:44],
    )


def show(oid):
    try:
        obj = http_json("%s/objects/%d" % (API, oid))
    except Exception as exc:
        print("  ! %d 失败 %s" % (oid, exc))
        return
    if not obj.get("isPublicDomain"):
        print("  x %d 非 PublicDomain" % oid)
        return
    print("  o " + brief(obj))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", action="append", default=[])
    ap.add_argument("--department-id", type=int, default=None)
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--ids", default="")
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()

    if args.ids:
        for oid in [x for x in args.ids.split(",") if x.strip()]:
            show(int(oid))
            time.sleep(args.delay)
        return

    for q in args.query:
        params = {"q": q, "hasImages": "true", "isPublicDomain": "true"}
        if args.department_id:
            params["departmentId"] = str(args.department_id)
        print("== q=%s dept=%s ==" % (q, args.department_id))
        try:
            data = http_json("%s/search?%s" % (API, urllib.parse.urlencode(params)))
        except Exception as exc:
            print("  搜索失败：%s" % exc)
            continue
        ids = (data.get("objectIDs") or [])[: args.limit]
        print("  命中 %d" % len(ids))
        for oid in ids:
            show(oid)
            time.sleep(args.delay)


if __name__ == "__main__":
    main()
