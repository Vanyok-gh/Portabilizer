"""Launch.bat: рабочая папка игры (bin + data), Portable.ps1 для образов дисков и реестра.
Запуск: python tests/test_launch_hooks.py (подключение образов и reg.exe проверяются только в Windows)."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

def make(exe_rel, data_dir=True, discs=False, registry=False):
    t = Path(tempfile.mkdtemp()) / "G_portable"; a = t / "App"
    exe = a / exe_rel; exe.parent.mkdir(parents=True); exe.write_bytes(b"MZ" + b"\0" * 600)
    if data_dir:
        (exe.parent.parent / "data").mkdir()
    if discs: (t / "Discs").mkdir()
    if registry: (t / "Registry").mkdir()
    P.finish(t, a, exe, lambda s: None, {}, system_root=str(t / "noroot"))
    return t, (t / "Launch.bat").read_text("utf-8")

# bin + data рядом: запуск из корня установки
t, bat = make(Path("program files/Eidos/TRAOD/bin/TRAOD.exe"))
check('start "" /D "%ROOT%App\\program files\\Eidos\\TRAOD" "%ROOT%App\\program files\\Eidos\\TRAOD\\bin\\TRAOD.exe"' in bat,
      "bin + data: рабочая папка - корень установки, exe остаётся в bin")
check(not (t / "Portable.ps1").exists(), "без Discs и Registry Portable.ps1 не создаётся")
# регистр имени папки
t, bat = make(Path("g/BIN/g.exe"))
check('/D "%ROOT%App\\g" ' in bat, "BIN в верхнем регистре тоже понимается")
# bin без data: как раньше
t, bat = make(Path("g/bin/g.exe"), data_dir=False)
check('/D "%ROOT%App\\g\\bin" ' in bat, "bin без data: рабочая папка не меняется")
# обычная программа
t, bat = make(Path("tool.exe"), data_dir=False)
check('/D "%ROOT%App\\" "%ROOT%App\\tool.exe"' in bat, "exe в корне App: как раньше")

# Discs: появляется Portable.ps1, и Launch.bat идёт через него
t, bat = make(Path("program files/Eidos/TRAOD/bin/TRAOD.exe"), discs=True)
ps = t / "Portable.ps1"
check(ps.is_file(), "Discs: Portable.ps1 создан")
check(ps.read_bytes()[:3] == b"\xef\xbb\xbf", "Portable.ps1 в UTF-8 с BOM (кириллица в пути не ломает PowerShell)")
check('if exist "%ROOT%Portable.ps1" (' in bat and "goto :end" in bat and ":end" in bat, "Launch.bat выбирает Portable.ps1")
check('-Root "%ROOT:~0,-1%"' in bat, "корень передаётся без завершающего \\ (иначе \\\" ломает кавычки)")
check('-Dir "App\\program files\\Eidos\\TRAOD"' in bat and '-Exe "App\\program files\\Eidos\\TRAOD\\bin\\TRAOD.exe"' in bat,
      "в Portable.ps1 передаются рабочая папка и exe")
check(bat.index("USERPROFILE=") < bat.index("Portable.ps1"), "профиль подменяется до запуска Portable.ps1")
check('-Dir "App"' in make(Path("tool.exe"), data_dir=False, discs=True)[1], "exe в корне App: -Dir App без \\ в конце")
txt = ps.read_text("utf-8-sig")
for need in ("Mount-DiskImage", "Dismount-DiskImage", "reg.exe import", "reg.exe export", "{ROOT}", "-Wait", "keys.txt", "Discs", "Registry"):
    check(need in txt, "Portable.ps1: " + need)
check("\\\\" not in txt, "в Portable.ps1 нет задвоенных обратных слэшей")
check(txt.count("{") == txt.count("}") and txt.count("(") == txt.count(")"), "скобки сбалансированы")
# только Registry
t, bat = make(Path("tool.exe"), data_dir=False, registry=True)
check((t / "Portable.ps1").is_file(), "Registry: Portable.ps1 создан")
print(f"хуки Launch.bat: {n} проверок пройдено")
