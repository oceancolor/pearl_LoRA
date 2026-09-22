import json,pathlib
T=pathlib.Path('f:/pearl_LoRA/data/train/images')
m={}
for g in sorted(T.glob('*.png')):
 cap=(T/(g.stem+'.txt')).read_text(encoding='utf-8').strip()
 m[g.name]={"full_path":str(g),"caption":cap,"repeats":1,"keep_tokens":2}
s=json.dumps(m,ensure_ascii=False,indent=2)
(T/'metadata.json').write_text(s,encoding='utf-8')
print(len(m))
