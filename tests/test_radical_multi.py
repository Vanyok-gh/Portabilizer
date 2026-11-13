"""Режим R для папок и нескольких источников. Запуск: python tests/test_radical_multi.py"""
import sys, tempfile, zipfile, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P
sys.path.insert(0, str(Path(__file__).resolve().parent))

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

def md5(b): return hashlib.md5(b).hexdigest().upper()

def make_disc(base):
    root = base / "ToV"; data = root / "Data"; data.mkdir(parents=True)
    (root / "gameInst.exe").write_bytes(b"MZ")
    c = b"EXE" * 100; h = md5(c); fid = f"RelicCOH.exe.{h}.NEW"
    (data / fid).write_bytes(c)
    lua = ('AppExeName = L"RelicCOH.exe"\r\nLocaleID = "English"\r\nAddedFiles = {\r\n'
           '  {Progress = 1, ID = "%s", Md5Sum = "%s", Path = L"\\\\RelicCOH.exe"},\r\n}\r\nAddedDirectories = {\r\n}\r\n' % (fid, h))
    with zipfile.ZipFile(data / "Install.lua.zip", "w") as z: z.writestr("Install.lua", lua)
    return root

# охранные проверки
check(P.radical_unsafe_source(Path("/")) != "", "корень нельзя")
check(P.radical_unsafe_source(Path.home()) != "", "домашнюю папку нельзя")
check(P.radical_unsafe_source(Path("/definitely/not/here")) == "не найден", "несуществующее нельзя")

with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    check(P.radical_unsafe_source(t) == "", "обычная папка можно")
    root = make_disc(t / "in")
    logs = []
    ok = P.portabilize(str(root), str(t / "ignored"), logs.append, "auto", "", radical=True, confirmed=True)
    out = root.parent / "ToV_portable"
    check(ok, "R собрал диск Relic из папки: " + "\n".join(logs))
    check((out / "App" / "RelicCOH.exe").is_file() and (out / "Launch.bat").is_file(), "результат рядом с исходной папкой")
    check(not root.exists(), "исходная папка удалена")
    check(not (t / "ignored").exists(), "результат не ушёл в «Куда»")

    # без confirmed ничего не делает
    root2 = make_disc(t / "in2")
    ok = P.portabilize(str(root2), str(t / "x"), logs.append, "auto", "", radical=True, confirmed=False)
    check(not ok and root2.exists(), "без подтверждения не трогаем")

    # опасный источник отклоняется
    ok = P.portabilize(str(Path.home()), str(t / "y"), logs.append, "auto", "", radical=True, confirmed=True)
    check(not ok, "домашняя папка отклонена")

    # cleanup не удаляет, если Launch.bat нет
    tgt = t / "tg"; (tgt / "App").mkdir(parents=True); (tgt / "App" / "a").write_text("1")
    src = t / "s"; src.mkdir(); (src / "f").write_text("1")
    res = P.radical_cleanup_multi([src], tgt, {}, logs.append)
    check(src.exists() and res["kept_reason"], "без Launch.bat источник остаётся")
    (tgt / "Launch.bat").write_text("x")
    res = P.radical_cleanup_multi([src], tgt, {}, logs.append)
    check(not src.exists() and res["deleted"], "с Launch.bat источник удалён")
    # результат внутри источника - не удаляем
    outer = t / "outer"; inner = outer / "r"; (inner / "App").mkdir(parents=True); (inner / "App" / "a").write_text("1"); (inner / "Launch.bat").write_text("x")
    res = P.radical_cleanup_multi([outer], inner, {}, logs.append)
    check(outer.exists(), "результат внутри источника - ничего не удаляем")
print(f"OK: {n} проверок")
