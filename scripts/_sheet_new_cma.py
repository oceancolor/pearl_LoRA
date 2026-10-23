"""只给「还没看过」的 cma 候选出联系表。

已看过的记在 data/crops/_review/_seen_cma.txt；每跑一次把本次的追加进去。
  python scripts/_sheet_new_cma.py <输出名>
"""
import pathlib
import subprocess
import sys

RAW = pathlib.Path("data/inbox/raw")
SEEN = pathlib.Path("data/crops/_review/_seen_cma.txt")
SEEN_INIT = {
    # 2026-10-23 前三张联系表已看过的
    "cma_107161", "cma_112858", "cma_115988", "cma_124005", "cma_131789", "cma_133012",
    "cma_136468", "cma_137313", "cma_137646", "cma_142535", "cma_142546", "cma_145966",
    "cma_146117", "cma_151967", "cma_154753", "cma_154754", "cma_154759", "cma_155591",
    "cma_155593", "cma_157290", "cma_161771", "cma_162216", "cma_162450", "cma_162469",
    "cma_162523", "cma_170078", "cma_170862", "cma_170864", "cma_314115", "cma_314125",
    "cma_314129", "cma_314141", "cma_314225", "cma_314236", "cma_314369", "cma_314415",
    "cma_314434", "cma_314436", "cma_314441", "cma_314443", "cma_314444", "cma_314446",
    "cma_314461", "cma_314463", "cma_314464", "cma_314472", "cma_314473", "cma_314477",
    "cma_314481", "cma_314490", "cma_314492", "cma_314493", "cma_314496", "cma_314499",
    "cma_314505", "cma_120873",
}

seen = set(SEEN.read_text(encoding="utf-8").split()) if SEEN.exists() else set(SEEN_INIT)
new = []
for d in sorted(list(RAW.glob("cma_*")) + list(RAW.glob("aic_*"))):
    if d.name in seen:
        continue
    p = d / "image.jpg"
    if p.exists():
        new.append((d.name, p))

if not new:
    sys.exit("没有新的 cma 候选")

print("新候选 %d 个：" % len(new))
for i, (n, _) in enumerate(new, 1):
    print("  %2d %s" % (i, n))

subprocess.run([sys.executable, "scripts/_sheet.py", sys.argv[1], *[str(p) for _, p in new],
                "--cell=150", "--cols=6"], check=True)
SEEN.write_text("\n".join(sorted(seen | {n for n, _ in new})), encoding="utf-8")
