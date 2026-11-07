"""Оцифровка дисковых игр (pzp_disc): реестр из msi -> .reg, перенос файлов с диска, патчи exe.
Запуск: python tests/test_disc.py"""
import sys, tempfile, glob
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pzp_disc as D

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

logs = []
log = logs.append

# --- .reg из записей
ents = [
    {"root": 2, "key": "SOFTWARE\\Core Design\\X\\1.0", "name": "InstalledPath", "value": "[INSTALLDIR]".replace("[INSTALLDIR]", "{INSTALLDIR}"), "kind": "sz"},
    {"root": 2, "key": "SOFTWARE\\Core Design\\X\\1.0", "name": "Language", "value": "1033", "kind": "dword"},
    {"root": 1, "key": "Software\\Y", "name": "", "value": "a\"b", "kind": "sz"},
]
t = D.reg_text(ents, "{ROOT}\\App\\program files\\G\\TRAOD")
check(t.startswith("Windows Registry Editor Version 5.00"), "заголовок .reg")
check('"InstalledPath"="{ROOT}\\\\App\\\\program files\\\\G\\\\TRAOD\\\\"' in t, "путь с {ROOT}, слэши удвоены, в конце слэш")
check('"Language"=dword:00000409' in t, "dword в hex")
check('[HKEY_CURRENT_USER\\SOFTWARE\\Core Design\\X\\1.0]' in t, "HKLM переведён в HKCU (админ не нужен)")
check('@="a\\"b"' in t, "кавычка в значении экранирована, пустое имя = @")

# --- перенос файлов с диска
with tempfile.TemporaryDirectory() as d:
    d = Path(d); root = d / "App"; game = root / "pf" / "TRAOD"
    (root / "Data" / "Audio").mkdir(parents=True); (root / "Data" / "Audio" / "front.AWD").write_bytes(b"1")
    (root / "Data" / "Audio" / "same.awd").write_bytes(b"new")
    (root / "Data" / "Maps").mkdir(); (root / "Data" / "Maps" / "m.gmx").write_bytes(b"2")
    (game / "data" / "audio").mkdir(parents=True); (game / "data" / "audio" / "SAME.AWD").write_bytes(b"old")
    (game / "bin").mkdir()
    k = D.merge_disc_layout(root, game, ["Data", "Bin", "DirectX9"], log)
    check(k == 2, f"перенесено 2 файла (третий уже есть), а не {k}")
    check((game / "data" / "audio" / "front.AWD").exists(), "файл из Data\\Audio попал в data\\audio")
    check(any(q.name.lower() == "maps" and (q / "m.gmx").exists() for q in (game / "data").iterdir()), "папка Maps создана в data")
    check((game / "data" / "audio" / "SAME.AWD").read_bytes() == b"old", "существующий файл не перезаписан")
    check(not (root / "Data" / "Maps").exists(), "пустая папка-источник убрана")

# --- патчи
sig = D.PATCHES[0]["sig"]
with tempfile.TemporaryDirectory() as d:
    d = Path(d); (d / "bin").mkdir()
    a = d / "bin" / "G_P4.exe"; a.write_bytes(b"MZ" + b"\x90" * 50 + sig + b"\x90" * 30)
    b = d / "bin" / "G.exe"; b.write_bytes(b"MZ" + b"\x90" * 100)
    r = D.apply_patches(d, log)
    check([x[2] for x in r] == ["patched"], f"пропатчен один файл: {r}")
    check(a.read_bytes()[2 + 50 + 8] == 0xEB, "jne -> jmp")
    check((d / "bin" / "G_P4.exe.bak").read_bytes()[2 + 50 + 8] == 0x75, "оригинал сохранён как .bak")
    check(b.read_bytes() == b"MZ" + b"\x90" * 100 and not (d / "bin" / "G.exe.bak").exists(), "exe без сигнатуры не тронут")
    r = D.apply_patches(d, log)
    check([x[2] for x in r] == ["already"], "повторный запуск: already")
    r = D.apply_patches(d, log, undo=True)
    check(a.read_bytes()[2 + 50 + 8] == 0x75, "undo возвращает оригинал")
    # два совпадения - не трогаем
    c = d / "bin" / "G2.exe"; c.write_bytes(b"MZ" + sig + b"\0" * 5 + sig)
    r = D.apply_patches(d, log)
    check(all(x[0] != c for x in r) and c.read_bytes() == b"MZ" + sig + b"\0" * 5 + sig, "неоднозначная сигнатура: не меняем")

# --- настоящий msi (если приложен)
real = glob.glob("/mnt/user-data/attachments/*/*Angel_Of_Darkness*.msi")
if real:
    a = D.analyze(real[0])
    check(a["labels"] == ["TRAOD1", "TRAOD2"], f"метки дисков: {a['labels']}")
    check(a["install_rel"] == ["program files", "Eidos Interactive", "TRAOD"], f"каталог установки: {a['install_rel']}")
    check(set(a["layout"]) == {"Bin", "Data"}, f"каталоги с диска: {a['layout']}")
    keys = {(e["key"], e["name"], e["value"], e["kind"]) for e in a["registry"]}
    check(("SOFTWARE\\Core Design\\TombRaiderAngelOfDarkness\\1.0", "Language", "1033", "dword") in keys, "Language=1033 dword")
    check(("SOFTWARE\\Core Design\\TombRaiderAngelOfDarkness\\1.0", "InstalledPath", "{INSTALLDIR}", "sz") in keys, "InstalledPath")

# --- полный проход digitize_disc_game на настоящем msi (если приложен)
if real:
    import portabilizer_v8 as P
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); app = d / "App"; tgt = d / "Out"; src = d / "disc"
        src.mkdir(); tgt.mkdir()
        game = app / "program files" / "Eidos Interactive" / "TRAOD"
        (game / "data" / "audio").mkdir(parents=True); (game / "bin").mkdir()
        (app / "Data" / "Audio").mkdir(parents=True); (app / "Data" / "Audio" / "frontend.AWD").write_bytes(b"x")
        (game / "bin" / "TRAOD_P4.exe").write_bytes(b"MZ" + sig + b"\0" * 9)
        msi = src / "x.msi"; msi.write_bytes(Path(real[0]).read_bytes())
        logs.clear()
        ok = P.digitize_disc_game(msi, app, tgt, log, None, {})
        check(ok, "digitize_disc_game сработал: " + "; ".join(logs))
        check((game / "data" / "audio" / "frontend.AWD").exists(), "файл с диска перенесён в data")
        reg = (tgt / "Registry").glob("*.reg")
        reg = list(reg)
        check(len(reg) == 1, "создан один .reg")
        txt = reg[0].read_text("utf-16")
        check("{ROOT}\\\\App\\\\program files\\\\Eidos Interactive\\\\TRAOD\\\\" in txt, "в .reg путь игры от {ROOT}")
        keys = (tgt / "Registry" / "keys.txt").read_text()
        check(keys.strip() == "HKEY_CURRENT_USER\\SOFTWARE\\Core Design\\TombRaiderAngelOfDarkness", "keys.txt: ключ без версии: " + keys)
        check((game / "bin" / "TRAOD_P4.exe.bak").exists(), "патч применён, .bak создан")
        check(not (tgt / "Discs").exists(), "без папки Data рядом с msi образ не строится")
        src2 = d / "disc2"; src2.mkdir(); (src2 / "Data").mkdir(); (src2 / "Data" / "f.bin").write_bytes(b"1234")
        msi2 = src2 / "x.msi"; msi2.write_bytes(msi.read_bytes())
        P.digitize_disc_game(msi2, app, tgt, log, None, {})
        iso = tgt / "Discs" / "TRAOD1.iso"
        check(iso.is_file() and iso.stat().st_size > 2048 * 16, "образ диска TRAOD1.iso собран")
print(f"Disc: {n} проверок пройдено")
