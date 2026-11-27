"""Запасные bat (v11.2): поиск Python у текущего пользователя и честная установка без прав администратора.
Проверяет текст файлов, не запуск: запуск проверяется руками на Windows."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMES = ("Portabilizer.bat", "Portabilizer (R).bat", "Portabilizer-py.bat")
bad = []


def check(cond, msg):
    if not cond:
        bad.append(msg)


files = {}
for n in NAMES:
    found = [p for p in ROOT.rglob(n) if ".git" not in p.parts]
    check(found, f"не найден {n}")
    if found:
        files[n] = found[0]

for n, p in files.items():
    raw = p.read_bytes()
    t = raw.decode("utf-8-sig")
    check(b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b""), f"{n}: нужны переводы строк CRLF")
    labels = {m.group(1).lower() for m in re.finditer(r"(?m)^:(\w+)", t)}
    for m in re.finditer(r"(?i)\bgoto\s+:?(\w+)", t):
        g = m.group(1).lower()
        check(g == "eof" or g in labels, f"{n}: goto на несуществующую метку {g}")
    for m in re.finditer(r"(?i)\bcall\s+:(\w+)", t):
        check(m.group(1).lower() in labels, f"{n}: call на несуществующую метку {m.group(1)}")
    check(":findpy" in t and "call :findpy" in t, f"{n}: нет поиска Python пользователя")
    check("InstallAllUsers=0" in t, f"{n}: установка должна быть для текущего пользователя")
    check("InstallAllUsers=1" not in t, f"{n}: нельзя ставить для всех пользователей")
    check(not re.search(r"(?i)runas|-Verb\s+RunAs|Start-Process|reg\s+add\s+hklm|setx\s+/m", t),
          f"{n}: запрос прав администратора или запись в систему не нужны")
    check(t.index("call :findpy") < t.index("goto nopy") if "goto nopy" in t else True,
          f"{n}: поиск Python пользователя должен идти до сообщения «не найден»")
    # установщик запускается только после вопроса и не раньше
    check(t.index("choice /c YN") < t.index("InstallAllUsers=0"), f"{n}: установка без вопроса")
    check("python.org" in t, f"{n}: нет ссылки на python.org для ручной установки")

if bad:
    print("\n".join("FAIL: " + b for b in bad))
    sys.exit(1)
print("ok: test_bat_python")
