"""pzp_cab: разбор cab без сжатия и MSZIP (на cab из tools/collect_redist). LZX проверен вручную на cab из vcredist."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import pzp_cab
import collect_redist as C

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

files = {"a.dll": b"A" * 70000, "b.dll": bytes(range(256)) * 300}
got = dict(pzp_cab.parse(C.cab_write(files)))
check(got == files, "cab MSZIP читается")
try:
    pzp_cab.parse(b"not a cab at all")
    check(False, "не cab")
except pzp_cab.CabError:
    check(True, "не cab - ошибка")
print(f"OK: {n} проверок")
