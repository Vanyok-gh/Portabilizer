"""7-Zip код 2 из-за символических ссылок (zip с macOS/Linux, например Xonotic) не считается провалом.
Запуск: python tests/test_symlink_errors.py"""
import os, stat, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

def fake_7z(d: Path, lines, rc) -> Path:
    """Поддельный 7z: печатает заданные строки и завершается с кодом rc."""
    f = d / "fake7z.py"
    body = "".join(f"sys.stdout.write({l + chr(10)!r})\n" for l in lines)
    f.write_text(f"#!{sys.executable}\nimport sys\n{body}sys.stdout.flush()\nsys.exit({rc})\n", encoding="utf-8")
    f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return f

SYM = "ERROR: Cannot create symbolic link : ______ : C:\\out\\Xonotic.app\\Contents\\MacOS\\libogg.dylib"
TAIL = ["Sub items Errors: 2", "Archives with Errors: 1"]

if os.name != "nt":
    real_find = P.find_tool
    try:
        with tempfile.TemporaryDirectory() as t:
            t = Path(t); arc = t / "a.zip"; arc.write_bytes(b"x")
            logs = []

            def go(lines, rc):
                P.find_tool = lambda *a, **k: str(fake_7z(t, lines, rc))
                P.EXTRACT_WARNINGS.clear()
                return P.extract(arc, "archive", t / "out", logs.append)

            check(go([SYM, SYM] + TAIL, 2) is True, "только символические ссылки: успех")
            check(P.EXTRACT_WARNINGS == ["символические ссылки не созданы"], f"предупреждение: {P.EXTRACT_WARNINGS}")
            check(any("символические ссылки" in l for l in logs), "в лог написано про ссылки")

            check(go([SYM, "ERROR: CRC Failed : C:\\out\\data.pk3"] + TAIL, 2) is False, "другая ошибка рядом: провал")
            check(go(["ERROR: Data Error : C:\\out\\data.pk3"], 2) is False, "без ссылок: провал")
            check(go([], 2) is False, "код 2 без ERROR: провал")
            check(go([SYM], 1) is True, "код 1 как и раньше успех")
            check(go([], 0) is True, "код 0 успех")
            # много строк: счётчик не зависит от размера хвоста вывода
            check(go([SYM] * 3000, 2) is True, "3000 ссылок: успех")
            check(P.run.sym_errors == 3000, f"посчитано {P.run.sym_errors}")
    finally:
        P.find_tool = real_find

print(f"OK: {n} проверок")
