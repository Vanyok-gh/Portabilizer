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

print("\nпровалов:", len(fails))
sys.exit(1 if fails else 0)
