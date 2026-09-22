import json,pathlib
C=pathlib.Path('f:/pearl_LoRA/data/crops');T=pathlib.Path('f:/pearl_LoRA/data/train/images')
for ln in (C/'_m.psv').read_text(encoding='utf-8').splitlines()[1:]:
 p=ln.split('|')
 cap=(T/(p[0]+'.txt')).read_text(encoding='utf-8').strip()
 d={"id":p[0],"license":p[1],"family":p[2]}
 d["style"]={"traits":p[6].split(','),"palette":p[7].split(',')}
 d["theme"]={"primary":p[3],"secondary":p[4].split(',') if p[4] else []}
 d["content"]=p[8].split(',')
 d["composition"]=p[5]
 d["caption_en"]=cap
 d["notes_zh"]=p[9]
 d["split"]="train"
 s=json.dumps(d,ensure_ascii=False,indent=2)
 (T/(p[0]+'.json')).write_text(s,encoding='utf-8')
print('ok')
