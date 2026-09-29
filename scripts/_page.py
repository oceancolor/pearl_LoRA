"""_page.py — api.php 被限流时，直接取 Commons 文件页 HTML 找年代证据。"""
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "decomineral-lora/1.0 (commons.wikimedia.org; non-commercial PD art dataset research)"}
PAGES = [
    "File:Shahnameh illustration - IMJ B69-0633.jpeg",
    "File:Shahnameh illustration - IMJ B69-0627.jpeg",
]
PAT = re.compile(r"(1[0-9]{3}|1[0-9]th|1[0-9]th century|[0-9]{1,2}th century)", re.I)
for title in PAGES:
    url = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
    try:
        req = urllib.request.Request(url, headers=UA)
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    except Exception as exc:
        print(title, "ERR", exc)
        continue
    hits = sorted(set(PAT.findall(html)))
    print("==", title)
    print("  长度", len(html), "年代候选:", hits[:12])
    for kw in ("Date", "date", "century"):
        for m in re.finditer(kw, html):
            seg = html[max(0, m.start() - 60):m.start() + 120]
            seg = re.sub(r"<[^>]+>", " ", seg)
            seg = re.sub(r"\s+", " ", seg)
            if PAT.search(seg):
                print("   |", seg[:160])
                break
