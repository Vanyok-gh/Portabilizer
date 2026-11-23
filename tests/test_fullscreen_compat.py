"""Слой совместимости в Launch.bat (оптимизация во весь экран) и подсказка про старую графику.
Запуск: python tests/test_fullscreen_compat.py"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P
import pzp_disc

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

# строка __COMPAT_LAYER
check(P.compat_line(False, False) == "", "без опций строки нет")
check(P.compat_line(True, False) == P.INVOKER_LINE, "только RunAsInvoker: прежняя строка не изменилась")
l = P.compat_line(False, True)
check('set "__COMPAT_LAYER=DISABLEDXMAXIMIZEDWINDOWEDMODE"' in l, f"только FSO: {l!r}")
l = P.compat_line(True, True)
check('set "__COMPAT_LAYER=RunAsInvoker DISABLEDXMAXIMIZEDWINDOWEDMODE"' in l, f"оба слоя через пробел: {l!r}")
check(all(x.endswith("\r\n") for x in P.compat_line(True, True).splitlines(True)), "строки с CRLF")

def make(nofso, exe_bytes=b"MZ" + b"\0" * 600):
    P.COMPAT_OPTIONS["nofso"] = nofso
    t = Path(tempfile.mkdtemp()) / "G_portable"; a = t / "App"; a.mkdir(parents=True)
    exe = a / "Game.exe"; exe.write_bytes(exe_bytes)
    logs = []
    try:
        P.finish(t, a, exe, logs.append, {}, system_root=str(t / "noroot"))
    finally:
        P.COMPAT_OPTIONS["nofso"] = False
    return (t / "Launch.bat").read_text("utf-8"), "\n".join(logs)

bat, _ = make(False)
check("__COMPAT_LAYER" not in bat, "по умолчанию слоя совместимости в Launch.bat нет")
bat, _ = make(True)
check('__COMPAT_LAYER=DISABLEDXMAXIMIZEDWINDOWEDMODE' in bat, "с галочкой слой записан в Launch.bat")
check(bat.index("__COMPAT_LAYER") < bat.index("start "), "слой задан до запуска игры")

# подсказка про старую графику
legacy = b"MZ" + b"\0" * 300 + b"DDRAW.dll\0" + b"\0" * 300
modern = b"MZ" + b"\0" * 600
with tempfile.TemporaryDirectory() as t:
    f = Path(t) / "a.exe"; f.write_bytes(legacy)
    check(pzp_disc.scan_exe_hints(f)["legacy_gfx"] is True, "ddraw.dll (любой регистр) найден")
    f.write_bytes(b"MZ" + b"\0" * 100 + b"d3d8.dll\0"); check(pzp_disc.scan_exe_hints(f)["legacy_gfx"] is True, "d3d8.dll найден")
    f.write_bytes(modern); check(pzp_disc.scan_exe_hints(f)["legacy_gfx"] is False, "современный exe без признака")
_, log = make(False, legacy)
check("старую графику" in log, "подсказка в логе для старого exe")
_, log = make(True, legacy)
check("старую графику" not in log, "с включённой галочкой подсказки нет")
_, log = make(False, modern)
check("старую графику" not in log, "для современного exe подсказки нет")
a = P.Advisor(); a.scan("Подсказка: exe использует старую графику (DirectDraw/Direct3D 8).")
check(a.items and a.items[0][1] == "info", "подсказка попадает в панель")

print(f"OK: {n} проверок")
