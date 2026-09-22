import json

IDS = ['met_44794', 'met_464559', 'met_464604', 'met_49571', 'met_54210', 'met_54211',
       'met_60654', 'met_60655', 'met_700091', 'met_814025', 'met_891631', 'met_891632']
for n, i in enumerate(IDS, 1):
    m = json.load(open(f'data/inbox/raw/{i}/meta.json', encoding='utf-8'))
    print(f"[{n}] {i} | {m.get('width')}x{m.get('height')}")
    print(f"    title: {m.get('title', '')}")
    print(f"    creator: {m.get('creator', '')} | date: {m.get('publication_year', '')} | dept: {m.get('department', '')}")
    print(f"    url: {m.get('page_url', '')}")
