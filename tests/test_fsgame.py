"""fsgame.ltx для игр на движке X-Ray: создаётся только когда его нет, а данные игры есть."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P  # noqa: E402

fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


def game(with_db=True, with_ltx=False, with_exe=True, folder=False):
    app = Path(tempfile.mkdtemp()) / "App"
    (app / "bin").mkdir(parents=True)
    if with_exe:
        (app / "bin" / "XR_3DA.exe").write_bytes(b"MZ")
    if with_db:
        (app / "gamedata.db0").write_bytes(b"x")
    if folder:
        (app / "gamedata").mkdir()
    if with_ltx:
        (app / "fsgame.ltx").write_text("custom", encoding="ascii")
    return app


logs = []
a = game()
check(P.ensure_fsgame(a, logs.append), "нет файла, есть архивы: создан")
b = (a / "fsgame.ltx").read_bytes()
check(b.startswith(b"$app_data_root$ = true| false| $fs_root$| _appdata_\\\r\n"), "содержимое и CRLF")
check(b"$game_data$     = false| true| $fs_root$| gamedata\\\r\n" in b, "путь к gamedata")
check(not (a / "bin" / "fsgame.ltx").exists(), "файл лежит в корне, а не в bin")
check(logs and "fsgame.ltx" in logs[0], "в журнале есть пояснение")

a = game(with_ltx=True)
check(not P.ensure_fsgame(a, logs.append) and (a / "fsgame.ltx").read_text() == "custom", "свой файл не трогаем")
check(P.ensure_fsgame(game(with_db=False, folder=True), logs.append), "распакованная папка gamedata тоже считается")
check(not P.ensure_fsgame(game(with_db=False), logs.append), "нет данных игры: ничего не создаём")
check(not P.ensure_fsgame(game(with_exe=False), logs.append), "нет XR_3DA.exe: ничего не создаём")

# xrEngine.exe (Чистое Небо, Зов Припяти)
a = game(with_exe=False)
(a / "bin" / "xrEngine.exe").write_bytes(b"MZ")
check(P.ensure_fsgame(a, logs.append) and (a / "fsgame.ltx").is_file(), "xrEngine.exe: fsgame.ltx создаётся тоже")

# рабочая папка X-Ray - корень игры, а не bin
def wd(files, dirs, exe="bin/xrEngine.exe"):
    base = Path(tempfile.mkdtemp()) / "App"
    (base / "bin").mkdir(parents=True)
    for f in files:
        (base / f).write_bytes(b"x")
    for d in dirs:
        (base / d).mkdir(parents=True, exist_ok=True)
    return P.work_dir(base, Path(exe))


check(wd([], ["gamedata"]) == Path("."), "рабочая папка: есть gamedata - корень игры")
check(wd(["fsgame.ltx"], []) == Path("."), "рабочая папка: есть fsgame.ltx - корень игры")
check(wd(["gamedata.db0"], []) == Path("."), "рабочая папка: есть gamedata.db0 - корень игры")
check(wd([], ["gamedata"], "bin/XR_3DA.exe") == Path("."), "рабочая папка: XR_3DA.exe тоже")
check(wd([], ["gamedata"], "bin/other.exe") == Path("bin"), "рабочая папка: чужой exe рядом с gamedata не трогаем")
check(wd([], []) == Path("bin"), "рабочая папка: нет данных X-Ray - папка exe")
check(wd([], ["data"], "bin/game.exe") == Path("."), "рабочая папка: прежнее правило с data работает")

print("\nпровалов:", len(fails))
sys.exit(1 if fails else 0)
