"""Запись ini-файлов из таблицы IniFile установщика (Locale.ini у Company of Heroes). Запуск: python tests/test_ini.py"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pzp_disc as D

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    f = t / "a" / "x.ini"
    check(D.write_ini_value(f, "locale", "lang", "Russian"), "новый файл создан")
    check(f.read_bytes().decode() == "[locale]\r\nlang=Russian\r\n", f"содержимое: {f.read_bytes().decode()!r}")
    check(not D.write_ini_value(f, "locale", "lang", "Russian"), "то же значение не меняет файл")
    check(D.write_ini_value(f, "locale", "lang", "English"), "значение обновляется")
    check(not D.write_ini_value(f, "locale", "lang", "French", only_if_absent=True), "action 1 не перезаписывает")
    D.write_ini_value(f, "other", "k", "v")
    D.write_ini_value(f, "locale", "extra", "1")
    txt = f.read_bytes().decode()
    check("[locale]\r\nlang=English\r\nextra=1\r\n" in txt and "[other]\r\nk=v" in txt, f"ключ в нужном разделе: {txt!r}")

    app = t / "App"; game = app / "program files" / "G"; (game / "Bug").mkdir(parents=True)
    ent = [{"dir": ["program files", "G"], "file": "Locale.ini", "section": "locale", "key": "lang", "value": "Russian", "action": 0},
           {"dir": ["program files", "G", "Bug"], "file": "Locale.ini", "section": "locale", "key": "lang", "value": "Russian", "action": 0},
           {"dir": ["nope", "deep", "x"], "file": "Locale.ini", "section": "s", "key": "k", "value": "v", "action": 0}]
    done = D.apply_ini_values(app, ent)
    check(len(done) == 2 and (game / "Locale.ini").is_file() and (game / "Bug" / "Locale.ini").is_file(), f"записаны оба: {done}")
    check(not (app / "nope").exists(), "чужое дерево не создаётся")
print(f"OK: {n} проверок")
