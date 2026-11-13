"""Доп. настройки: убрать лишнее и сжатие NTFS (команда подменяется). Запуск: python tests/test_slim.py"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

with tempfile.TemporaryDirectory() as t:
    t = Path(t); app = t / "App"; (app / "CoH").mkdir(parents=True)
    keep = ["Game.exe", "d.dll", "Readme_English.txt", "CoH/data.sga", "CoH/vcredist_x86.exe"]
    drop = ["vcredist_x86.exe", "dxsetup.exe", "Uninstall_English.exe", "FakeCOHMSI_x.msi", "removeFakeMSI.bat",
            "Readme_German.txt", "Readme_French.txt"]
    for f in keep + drop:
        (app / f).write_bytes(b"x" * 10)
    logs = []
    freed = P.trim_extras(app, logs.append)
    check(freed == 10 * len(drop), f"освобождено {freed}")
    check(all(not (app / f).exists() for f in drop), "лишнее удалено")
    check(all((app / f).exists() for f in keep), "нужное и вложенные папки целы")

    # если английского нет, остаётся один Readme
    app2 = t / "o2" / "App"; app2.mkdir(parents=True)
    for f in ("Readme_Czech.txt", "Readme_German.txt", "a.exe"):
        (app2 / f).write_text("x")
    P.trim_extras(app2, logs.append)
    check(sorted(x.name for x in app2.iterdir()) == ["Readme_Czech.txt", "a.exe"], "остался один Readme")

    # compress: команда подменена
    calls = []
    check(P.compress_folder(app, logs.append, run_cmd=lambda c: calls.append(c) or True), "compress ok")
    check(calls and calls[0][:2] == ["compact", "/c"] and str(app) in calls[0][2], f"команда: {calls}")
    check(P.compress_folder(app, logs.append, run_cmd=lambda c: False) is False, "ошибка команды не роняет")
    check(P.compress_folder(app, logs.append) is False, "вне Windows пропуск")

    # apply_slim: флаги
    calls.clear()
    P.apply_slim(t, logs.append, options={"trim": False, "compress": False}, run_cmd=lambda c: calls.append(c) or True)
    check(not calls, "оба выключены - ничего не делаем")
    P.apply_slim(t, logs.append, options={"trim": False, "compress": True}, run_cmd=lambda c: calls.append(c) or True)
    check(len(calls) == 1, "включено сжатие")
print(f"OK: {n} проверок")
