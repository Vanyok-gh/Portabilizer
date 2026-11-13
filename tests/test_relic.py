"""Установщик Relic: разбор Install.lua, раскладка из Data (файл и .zip), MD5, реестр, VC80 через подмену expand.
Запуск: python tests/test_relic.py"""
import hashlib, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pzp_relic as R
import portabilizer_v8 as P

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

def md5(b): return hashlib.md5(b).hexdigest().upper()

def make_disc(base, break_one=False, drop_one=False):
    root = base / "ToV"; data = root / "Data"; data.mkdir(parents=True)
    (root / "gameInst.exe").write_bytes(b"MZ")
    files = {r"\RelicCOH.exe": b"EXE" * 100, r"\CoH\Engine\a.sga": b"SGA" * 1000, r"\validators\v.dat": b"V"}
    rows, dirs = [], [r"\CoH", r"\CoH\Engine", r"\validators"]
    for i, (p, c) in enumerate(files.items()):
        h = md5(c); fid = f"{p.split(chr(92))[-1]}.{h}.NEW"
        rows.append('  {Progress = 1, ID = "%s", Md5Sum = "%s", Path = L"%s"},' % (fid, h, p.replace("\\", "\\\\")))
        payload = c + (b"!" if break_one and i == 1 else b"")
        if drop_one and i == 2:
            continue
        if i % 2:   # половина - в zip, имя члена = ID
            with zipfile.ZipFile(data / (fid + ".zip"), "w") as z: z.writestr(fid, payload)
        else:
            (data / fid).write_bytes(payload)
    lua = ('AppName = L"Company of Heroes"\r\nAppExeName = L"RelicCOH.exe"\r\nLocaleID = "English"\r\n'
           'NewVersion = L"2.0.0.1"\r\nCohKeyPath = L"HKEY_LOCAL_MACHINE\\\\SOFTWARE\\\\THQ\\\\Company of Heroes"\r\n'
           'AddedFiles = {\r\n' + "\r\n".join(rows) + '\r\n}\r\nAddedDirectories = {\r\n' +
           "\r\n".join('  {Progress = 1, Path = L"%s"},' % d.replace("\\", "\\\\") for d in dirs) + '\r\n}\r\n')
    with zipfile.ZipFile(data / "Install.lua.zip", "w") as z: z.writestr("Install.lua", lua)
    with zipfile.ZipFile(data / "Readme_English.txt.zip", "w") as z: z.writestr("Readme_English.txt", "hi")
    return root

with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    root = make_disc(t)
    check(R.find_root(t) == root, "корень диска найден на глубине 1")
    check(R.find_root(root) == root, "корень диска - сама папка")
    check(R.find_root(t / "nope") is None, "нет папки - нет корня")
    plan = R.parse_script(R.read_script(root))
    check(len(plan["files"]) == 3 and len(plan["dirs"]) == 3, f"разбор списков: {plan}")
    check(plan["files"][1][2] == ("CoH", "Engine", "a.sga"), "путь с подпапками")
    check(plan["exe"] == "RelicCOH.exe" and plan["locale"] == "English", "скаляры")
    check(R._clean_path("\\..\\x") is None and R._clean_path("C:\\x") is None, "опасные пути отклоняются")

    logs = []; seen = []
    app = t / "out" / "App"
    res = R.install(root, app, logs.append, progress=lambda d, tt: seen.append((d, tt)))
    check(not res["missing"] and not res["bad_md5"], f"всё на месте: {res}")
    check((app / "CoH/Engine/a.sga").read_bytes() == b"SGA" * 1000, "файл из zip распакован верно")
    check((app / "RelicCOH.exe").is_file() and (app / "validators/v.dat").is_file(), "файлы разложены")
    check((app / "Readme_English.txt").read_text() == "hi" and res["extras"] == 1, "Readme из zip")
    check(seen[-1] == (3, 3), "прогресс дошёл до конца")
    check(not list(app.rglob("*.part")), "временных файлов не осталось")

    bad = R.install(make_disc(t / "b", break_one=True), t / "o2" / "App", logs.append)
    check(len(bad["bad_md5"]) == 1, "битый файл замечен по MD5")
    miss = R.install(make_disc(t / "m", drop_one=True), t / "o3" / "App", logs.append)
    check(len(miss["missing"]) == 1, "отсутствующий файл замечен")
    try:
        R.install(root, t / "o4" / "App", logs.append, stop=lambda: True); check(False, "отмена")
    except InterruptedError:
        check(True, "отмена прерывает")

    text, key = R.registry_text(res)
    check(key == "HKEY_CURRENT_USER\\SOFTWARE\\THQ\\Company of Heroes" and "{ROOT}" in text and "Installed" in text, "реестр в HKCU")

    # VC80: заглушка вместо expand; без vcredist.zip - спокойный пропуск
    check(R.vc80_runtime(root, app, logs.append, run=lambda c: 0) is False, "без vcredist.zip пропуск")

    # сквозной прогон: одна папка диска -> готовый portable
    logs = []
    ok = P.portabilize(str(root), str(t / "res"), logs.append, "auto", "")
    out = t / "res" / "ToV_portable"
    check(ok, "portabilize собрал: " + "\n".join(logs))
    check((out / "Launch.bat").is_file(), "Launch.bat создан")
    check((out / "App" / "RelicCOH.exe").is_file(), "App/RelicCOH.exe")
    check((out / "Registry" / "Company of Heroes.reg").is_file(), ".reg создан")
    check("THQ" in (out / "Registry" / "keys.txt").read_text(), "keys.txt")
    check("RelicCOH.exe" in (out / "Launch.bat").read_text(errors="ignore"), "Launch.bat запускает RelicCOH.exe")
    check(not (out / "Extracted_discs").exists(), "копии диска нет")

# диск Relic внутри zip-архива (папка "COH TOV" внутри)
with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    d = make_disc(t / "src"); (d.parent / "COH TOV").mkdir(); d.rename(d.parent / "COH TOV" / "disc")
    zp = t / "COH TOV.zip"
    with zipfile.ZipFile(zp, "w") as z:
        for f in (t / "src" / "COH TOV").rglob("*"):
            if f.is_file(): z.write(f, f.relative_to(t / "src").as_posix())
    logs = []
    def fake_extract(f, kind, dest, log, job=None):      # 7z.exe в Linux не запускается: распаковываем zipfile
        with zipfile.ZipFile(f) as z: z.extractall(dest)
        return True
    P.extract = fake_extract
    ok = P.portabilize(str(zp), str(t / "res"), logs.append, "auto", "")
    out = t / "res" / "COH TOV_portable"
    check(ok, "архив с диском Relic собран: " + "\n".join(logs))
    check((out / "App" / "RelicCOH.exe").is_file() and (out / "Launch.bat").is_file(), "App и Launch.bat")
    check(not (out / "Extracted_archive").exists(), "распакованный архив удалён")
    check((out / "App" / "CoH" / "Engine" / "a.sga").read_bytes() == b"SGA" * 1000, "файлы на месте после переноса")
# перенос: источник исчезает
with tempfile.TemporaryDirectory() as t:
    t = Path(t); root = make_disc(t / "s")
    res = R.install(root, t / "o" / "App", lambda m: None, consume=True)
    check(not res["bad_md5"] and not res["missing"], "перенос: всё сошлось")
    left = [x.name for x in (root / "Data").iterdir() if x.name.endswith(".NEW") or x.name.endswith(".NEW.zip")]
    check(not left, f"перенос: источники убраны: {left}")
print(f"OK: {n} проверок")
