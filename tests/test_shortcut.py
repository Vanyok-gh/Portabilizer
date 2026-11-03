"""Ярлык на рабочем столе: выбор иконки, имя, Create_Shortcut.bat. Запуск: python tests/test_shortcut.py
(создание самого .lnk проверяется только в Windows; здесь проверяется всё, что от него зависит)."""
import re, struct, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

def make_pe(path, icon):
    """Минимальный PE32: секция .rsrc с корневым каталогом ресурсов (тип 14 = иконка, если icon)."""
    ids = [3, 14] if icon else [3, 16]                       # 3 - RT_ICON, 14 - RT_GROUP_ICON, 16 - RT_VERSION
    rs = struct.pack("<IIHHHH", 0, 0, 0, 0, 0, len(ids)) + b"".join(struct.pack("<II", i, 0x80000000) for i in ids)
    rs += b"\0" * 64
    hdr = bytearray(0x400)
    hdr[:2] = b"MZ"; struct.pack_into("<I", hdr, 0x3C, 0x80)
    hdr[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", hdr, 0x84, 0x14C, 1, 0, 0, 0, 224, 0x102)      # COFF: 1 секция, opt=224
    opt = 0x98
    struct.pack_into("<H", hdr, opt, 0x10B)
    struct.pack_into("<II", hdr, opt + 96 + 2 * 8, 0x1000, len(rs))               # DataDirectory[2] = ресурсы
    sec = opt + 224
    hdr[sec:sec + 8] = b".rsrc\0\0\0"
    struct.pack_into("<IIII", hdr, sec + 8, len(rs), 0x1000, len(rs), 0x400)
    Path(path).write_bytes(bytes(hdr) + rs)

tmp = Path(tempfile.mkdtemp())
a = tmp / "a.exe"; make_pe(a, True)
b = tmp / "b.exe"; make_pe(b, False)
check(P.pe_has_icon(a) is True, "exe с иконкой")
check(P.pe_has_icon(b) is False, "exe без иконки")
(tmp / "x.txt").write_text("не exe")
check(P.pe_has_icon(tmp / "x.txt") is None and P.pe_has_icon(tmp / "нет.exe") is None, "не PE и нет файла -> None")
(tmp / "short.exe").write_bytes(b"MZ" + b"\0" * 20)
check(P.pe_has_icon(tmp / "short.exe") is None, "обрезанный PE -> None, без падения")

# выбор иконки
t = tmp / "Игра_portable"; app = t / "App"; (app / "bin").mkdir(parents=True)
make_pe(app / "bin" / "game.exe", True)
check(P.pick_icon(app, app / "bin" / "game.exe") == ("App\\bin\\game.exe", 0), "иконка из главного exe")
make_pe(app / "bin" / "noicon.exe", False)
(app / "bin" / "other.ico").write_bytes(b"ico"); (app / "bin" / "noicon.ico").write_bytes(b"ico")
check(P.pick_icon(app, app / "bin" / "noicon.exe") == ("App\\bin\\noicon.ico", 0), ".ico с тем же именем главнее чужого")
(app / "bin" / "noicon.ico").unlink()
check(P.pick_icon(app, app / "bin" / "noicon.exe") == ("App\\bin\\other.ico", 0), "любой .ico рядом")
(app / "bin" / "other.ico").unlink()
(app / "Launcher.exe").write_bytes(b"x")
(app / "AUTORUN.INF").write_text("[autorun]\nopen=Launcher.exe\nicon=Launcher.exe,3\n")
check(P.autorun_icon(app) == ("Launcher.exe", 3), "autorun.inf: icon=файл,номер")
check(P.pick_icon(app, app / "bin" / "noicon.exe") == ("App\\Launcher.exe", 3), "иконка диска из autorun.inf")
(app / "AUTORUN.INF").unlink()
check(P.pick_icon(app, app / "bin" / "noicon.exe") is None, "иконки нигде нет -> None")

# имя
check(P.shortcut_name(Path("C:/x/Tomb Raider_portable")) == "Tomb Raider", "имя без _portable")
check(P.shortcut_name(Path("a/Lara: Croft? 100%_portable")) == "Lara Croft 100", "недопустимые символы убраны")
check(P.shortcut_name(Path("a/_portable")) == "Portabilizer", "пустое имя -> запасное")

# Create_Shortcut.bat
bat, name, icon = P.write_shortcut_script(t, app, app / "bin" / "game.exe")
text = bat.read_text("utf-8")
check(bat.name == "Create_Shortcut.bat" and name == "Игра" and icon == ("App\\bin\\game.exe", 0), "результат write_shortcut_script")
check('set "PZ_NAME=Игра"' in text and 'set "PZ_ICON=App\\bin\\game.exe"' in text and 'set "PZ_IDX=0"' in text, "значения подставлены")
check("@NAME@" not in text and "@ICON@" not in text and "@IDX@" not in text, "меток не осталось")
check("\r\n" not in text.replace("\r\n", "\n") and "Launch.bat" in text and "GetFolderPath('Desktop')" in text, "скрипт: рабочий стол и Launch.bat")
ps = re.search(r'-Command "(.*)"\n', text).group(1)
check('"' not in ps and "%" not in ps, "внутри команды PowerShell нет кавычек и процентов, которые сломают cmd")
check(ps.count("(") == ps.count(")") and ps.count("{") == ps.count("}") and ps.count("'") % 2 == 0, "скобки и кавычки в PowerShell сбалансированы")
bat2, _, _ = P.write_shortcut_script(t, app, app / "bin" / "noicon.exe", name="100% Игра")
check('PZ_NAME=100%% Игра' in bat2.read_text("utf-8") and 'set "PZ_ICON="' in bat2.read_text("utf-8"), "% удваивается, без иконки поле пустое")

# finish(): вопрос о ярлыке и запись скрипта (Linux: создание .lnk не выполняется)
logs = []
t2 = tmp / "Программа_portable"; a2 = t2 / "App"; a2.mkdir(parents=True); make_pe(a2 / "prog.exe", True)
asked = []
info = {"shortcut_prompt": lambda nm, ic: asked.append((nm, ic)) or False}
P.finish(t2, a2, a2 / "prog.exe", logs.append, info, system_root=str(tmp / "noroot"))
check((t2 / "Launch.bat").is_file() and (t2 / "Create_Shortcut.bat").is_file(), "finish пишет Launch.bat и Create_Shortcut.bat")
check(asked == [("Программа", True)] and info["shortcut"]["name"] == "Программа", "вопрос задан с именем и признаком иконки")
logs2 = []; t3 = tmp / "Без_portable"; a3 = t3 / "App"; a3.mkdir(parents=True); make_pe(a3 / "p.exe", False)
P.finish(t3, a3, a3 / "p.exe", logs2.append, {}, system_root=str(tmp / "noroot"))
check(any("Иконку для ярлыка найти не удалось" in x for x in logs2), "без иконки и без вопроса: сообщение в журнал")
print("ярлык на рабочем столе:", n, "проверок пройдено")
