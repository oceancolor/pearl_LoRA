import json
import urllib.parse
import urllib.request

UA = {"User-Agent": "decomineral-lora/1.0 (commons.wikimedia.org; non-commercial PD art dataset research)"}
API = "https://commons.wikimedia.org/w/api.php"
T = ["File:Shahnameh illustration - IMJ B69-0633.jpeg",
     "File:Shahnameh illustration - IMJ B69-0627.jpeg"]
params = {"action": "query", "titles": "|".join(T), "prop": "imageinfo",
          "iiprop": "extmetadata", "format": "json", "formatversion": "2"}
r = json.loads(urllib.request.urlopen(
    urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA),
    timeout=30).read().decode())
for p in r["query"]["pages"]:
    print("==", p["title"])
    em = (p.get("imageinfo") or [{}])[0].get("extmetadata", {})
    for k, v in em.items():
        s = str(v.get("value", ""))
        if any(w in k.lower() for w in ("date", "year", "descr", "object")) or any(
                w in s.lower() for w in ("century", "1[0-9]{3}")):
            print("  ", k, "=", s[:160])
