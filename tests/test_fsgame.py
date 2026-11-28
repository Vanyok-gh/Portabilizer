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

# xrEngine.exe
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

# абсолютный путь данных игры из установщика
ABS = (";abbreviation = recurs|notif|root|add\r\n"
       "$game_data$ = false| true| $fs_root$| gamedata\r\n"
       "$app_data_root$\t\t= true|\tfalse|\tC:\\Users\\Someone\\DOCUME~1\\GAME~1\r\n"
       "$logs$ = true| false| $app_data_root$| logs\r\n")


def fx(text, exe="bin/xrEngine.exe", files=("gamedata.db0",)):
    app = Path(tempfile.mkdtemp()) / "App"
    (app / "bin").mkdir(parents=True)
    (app / exe).write_bytes(b"MZ")
    for n in files:
        (app / n).write_bytes(b"x")
    if text is not None:
        (app / "fsgame.ltx").write_bytes(text.encode("latin-1"))
    return app


logs = []
a = fx(ABS)
check(P.fix_fsgame_paths(a, logs.append), "абсолютный путь данных заменён")
new = (a / "fsgame.ltx").read_bytes().decode("latin-1")
check("$app_data_root$ = true| false| $fs_root$| _appdata_\\\r\n" in new, "новая строка: флаги сохранены, путь App\\_appdata_")
check("C:\\Users" not in new, "старого пути не осталось")
check(new.replace("$app_data_root$ = true| false| $fs_root$| _appdata_\\", "X") .count("\r\n") == ABS.count("\r\n"),
      "окончания строк CRLF сохранены")
check(new.splitlines()[0] == ABS.splitlines()[0] and new.splitlines()[1] == ABS.splitlines()[1]
      and new.splitlines()[3] == ABS.splitlines()[3], "остальные строки не тронуты")
check((a / "fsgame.ltx.orig").read_bytes().decode("latin-1") == ABS, "оригинал сохранён как fsgame.ltx.orig")
check(logs and "_appdata_" in logs[0] and "C:\\Users" in logs[0], "в журнале старый путь и новый")
check(not P.fix_fsgame_paths(a, logs.append), "повторный запуск ничего не меняет")

b = fx(ABS.replace("C:\\Users\\Someone", "\\\\server\\share"))
check(P.fix_fsgame_paths(b, logs.append), "сетевой путь заменяется")
c = fx(ABS.replace("C:\\Users\\Someone\\DOCUME~1\\GAME~1", "C:/Users/Someone/docs"))
check(P.fix_fsgame_paths(c, logs.append), "путь с прямыми слэшами заменяется")
rel = "$app_data_root$ = true| false| $fs_root$| _appdata_\\\r\n"
d = fx(rel)
check(not P.fix_fsgame_paths(d, logs.append) and (d / "fsgame.ltx").read_bytes() == rel.encode("latin-1")
      and not (d / "fsgame.ltx.orig").exists(), "относительный путь не трогаем")
cm = fx(";$app_data_root$ = true| false| C:\\Users\\Someone\\x\r\n")
check(not P.fix_fsgame_paths(cm, logs.append), "закомментированная строка не трогается")
check(not P.fix_fsgame_paths(fx(None), logs.append), "нет fsgame.ltx: ничего")
check(not P.fix_fsgame_paths(fx(ABS, exe="bin/other.exe"), logs.append), "не X-Ray: ничего")
e = fx(ABS, exe="bin/XR_3DA.exe")
check(P.fix_fsgame_paths(e, logs.append), "XR_3DA.exe тоже")
(e / "fsgame.ltx.orig").write_bytes(b"keep")
(e / "fsgame.ltx").write_bytes(ABS.encode("latin-1"))
P.fix_fsgame_paths(e, logs.append)
check((e / "fsgame.ltx.orig").read_bytes() == b"keep", "уже существующий .orig не перезаписывается")

print("\nпровалов:", len(fails))
sys.exit(1 if fails else 0)
