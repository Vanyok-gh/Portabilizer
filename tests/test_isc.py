"""InstallShield-диск (setup.exe + data1.hdr + dataN.cab): разбор, выбор файлов игры, распаковка с MD5.
Кабинет собирается тут же по формату InstallShield 12 (проверено на настоящем диске).
Запуск: python tests/test_isc.py"""
import hashlib, os, struct, sys, tempfile, zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pzp_isc as I
import portabilizer_v8 as P

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1


def pack(data: bytes) -> bytes:
    out = b""
    for i in range(0, len(data), 30000):          # куски: случайные данные не должны переполнить 2 байта длины
        c = zlib.compressobj(9, zlib.DEFLATED, -15)
        z = c.compress(data[i:i + 30000]) + c.flush()
        out += struct.pack("<H", len(z)) + z
    return out


def build(dest: Path, dirs, files, groups, version=0x020004B0):
    """files: dict(name, dir, data, vol, kind: z|raw|loose|invalid). groups: [(имя, первый, последний)]."""
    vols = {}
    recs = []
    for f in files:
        data = f["data"]
        kind = f["kind"]
        md5 = hashlib.md5(data).digest()
        if kind in ("z", "raw"):
            blob = pack(data) if kind == "z" else data
            v = vols.setdefault(f["vol"], bytearray(b"\0" * 0x200))
            doff = len(v)
            v += blob
            flags = 4 if kind == "z" else 0
            recs.append(dict(flags=flags, size=len(data), comp=len(blob), doff=doff, md5=md5))
        elif kind == "loose":
            recs.append(dict(flags=0, size=len(data), comp=len(data), doff=0, md5=md5))
        else:
            recs.append(dict(flags=12, size=0, comp=0, doff=0x200, md5=hashlib.md5(b"").digest()))
    # область описания: фиксированная часть, имена групп, описания групп, цепочки
    desc = bytearray(0x280)
    pool = bytearray()
    heads = []
    for i, (gname, a, b) in enumerate(groups):
        name_off = len(desc) + len(pool)
        pool += gname.encode() + b"\0"
        heads.append((name_off, a, b))
    gdesc_off = {}
    area = bytearray()
    base = len(desc) + len(pool)
    for i, (name_off, a, b) in enumerate(heads):
        g = bytearray(0x40)
        struct.pack_into("<I", g, 0, name_off)
        struct.pack_into("<I", g, 0x16, a)
        struct.pack_into("<I", g, 0x1A, b)
        gdesc_off[i] = base + len(area)
        area += g
    chain_off = {}
    cbase = base + len(area)
    chain = bytearray()
    for i, (name_off, a, b) in enumerate(heads):
        chain_off[i] = cbase + len(chain)
        chain += struct.pack("<3I", name_off, gdesc_off[i], 0)
    for i in range(len(heads)):
        struct.pack_into("<I", desc, 0x3E + 4 * i, chain_off[i])
    descarea = desc + pool + area + chain
    fto = len(descarea)
    # таблица файлов: смещения папок, строки, записи
    strings = bytearray()
    off_base = 4 * len(dirs)
    dir_offs = []
    for d in dirs:
        dir_offs.append(off_base + len(strings)); strings += d.encode() + b"\0"
    name_offs = []
    for f in files:
        name_offs.append(off_base + len(strings)); strings += f["name"].encode() + b"\0"
    fto2 = off_base + len(strings)
    table = bytearray(b"".join(struct.pack("<I", o) for o in dir_offs)) + strings
    for i, (f, r) in enumerate(zip(files, recs)):
        rec = bytearray(I.DESC_SIZE)
        struct.pack_into("<H", rec, 0, r["flags"]); struct.pack_into("<I", rec, 2, r["size"])
        struct.pack_into("<I", rec, 10, r["comp"]); struct.pack_into("<I", rec, 18, r["doff"])
        rec[26:42] = r["md5"]; struct.pack_into("<I", rec, 58, name_offs[i])
        struct.pack_into("<H", rec, 62, dirs.index(f["dir"])); struct.pack_into("<H", rec, 85, f["vol"])
        table += rec
    struct.pack_into("<I", descarea, 0x0C, fto)
    struct.pack_into("<I", descarea, 0x14, len(table)); struct.pack_into("<I", descarea, 0x18, len(table))
    struct.pack_into("<I", descarea, 0x1C, len(dirs)); struct.pack_into("<I", descarea, 0x28, len(files))
    struct.pack_into("<I", descarea, 0x2C, fto2)
    body = bytes(descarea) + bytes(table)
    hdr = bytearray(0x200) + body
    struct.pack_into("<5I", hdr, 0, I.SIGNATURE, version, 0, 0x200, len(body))
    (dest / "data1.hdr").write_bytes(bytes(hdr))
    for v, blob in vols.items():
        struct.pack_into("<2I", blob, 0, I.SIGNATURE, version)
        (dest / f"data{v}.cab").write_bytes(bytes(blob))


BIG = os.urandom(70000) + b"A" * 200000        # много кусков
FILES = [
    dict(name="", dir="", data=b"", vol=1, kind="invalid"),
    dict(name="quick.bundle", dir="", data=BIG, vol=2, kind="z"),
    dict(name="ESRB.bik", dir="movies", data=b"bik" * 5000, vol=2, kind="z"),
    dict(name="hud.xml", dir="", data=b"<hud/>", vol=2, kind="z"),
    dict(name="menu.xml", dir="strings", data=b"<fr/>" * 100, vol=2, kind="z"),
    dict(name="context.xml", dir="", data=b"uk", vol=2, kind="raw"),
    dict(name="context.xml", dir="", data=b"fr!", vol=2, kind="raw"),
    dict(name="graw2.exe", dir="", data=b"MZ" + b"E" * 3000, vol=1, kind="loose"),
    dict(name="PhysX_Setup.exe", dir="", data=b"MZ" + b"P" * 500, vol=1, kind="loose"),
    dict(name="Reader.exe", dir="", data=b"MZ" + b"R" * 400, vol=1, kind="loose"),
    dict(name="InstallerUtil.dll", dir="", data=b"dll", vol=2, kind="z"),
    dict(name="corecomp.ini", dir="", data=b"<core/>", vol=2, kind="z"),
    dict(name="setup.inx", dir="", data=b"inx", vol=1, kind="loose"),
    dict(name="dx.cab", dir="", data=b"dx", vol=2, kind="z"),
    dict(name="menu.xml", dir="strings", data=b"<de/>", vol=2, kind="z"),
]
GROUPS = [("CommonBundles", 1, 1), ("CommonData", 2, 2), ("CommonSettings", 3, 3), ("DataFR", 4, 4),
          ("ContextUK", 5, 5), ("ContextFR", 6, 6), ("Arch", 7, 7), ("Ageia", 8, 8), ("Acrobat", 9, 9),
          ("CommonDll", 10, 10), ("<Support>Script", 11, 12), ("DirectX", 13, 13), ("DataGer", 14, 14)]
DIRS = ["", "movies", "strings"]


with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    disc = t / "disc"; (disc / "Redist").mkdir(parents=True)
    build(disc, DIRS, FILES, GROUPS)
    # внешние файлы лежат на диске в разных местах
    (disc / "graw2.exe").write_bytes(FILES[7]["data"])
    (disc / "Redist" / "PhysX_Setup.exe").write_bytes(FILES[8]["data"])
    (disc / "Redist" / "Reader.exe").write_bytes(FILES[9]["data"])
    (disc / "setup.inx").write_bytes(b"inx")
    (disc / "setup.exe").write_bytes(b"MZ" + b"\0" * 100)

    # --- разбор
    cab = I.open_cabinet(disc / "setup.exe")
    check(cab.major == 12, f"версия {cab.major}")
    check(len(cab.entries) == len(FILES), "файлов в таблице")
    check(cab.entries[1].relpath == "quick.bundle" and cab.entries[2].relpath == "movies\\ESRB.bik", "пути")
    check(not cab.entries[0].valid and cab.entries[7].loose, "invalid и loose")
    check([g.name for g in cab.groups][:3] == ["CommonBundles", "CommonData", "CommonSettings"], "группы")
    check(I.looks_like_installshield(disc / "setup.exe") and not I.looks_like_installshield(t / "x.exe"), "детект")

    # --- выбор файлов
    files, redist, skipped = I.select_files(cab, "en")
    got = sorted(r.replace(os.sep, "/") for _, r in files)
    check(got == ["bundles/quick.bundle", "context.xml", "graw2.exe", "movies/ESRB.bik", "settings/hud.xml"],
          f"en: {got}")
    check([r for _, r in redist] == ["PhysX_Setup.exe"], "PhysX в redist")
    sk = [s[0] for s in skipped]
    check("DataFR" in sk and "Acrobat" in sk and "DirectX" in sk and "<Support>Script" in sk and "CommonDll" in sk, f"пропущены: {sk}")
    sk_counts = dict(skipped)
    check(sk_counts["<Support>Script"] == 2,
          f"<Support>Script пропускается целиком (InstallerUtil.dll и corecomp.ini): {sk_counts['<Support>Script']}")
    fr, _, _ = I.select_files(cab, "fr")
    frs = sorted(r.replace(os.sep, "/") for _, r in fr)
    check("strings/menu.xml" in frs and dict((r.replace(os.sep, '/'), e) for e, r in fr)["context.xml"].size == 3, f"fr: {frs}")

    # --- распаковка
    out = t / "App"
    logs = []
    count, size, errors = I.extract_game(cab, out, "en", logs.append)
    check(count == 5 and not errors, f"извлечено {count}, ошибки {errors}")
    check((out / "bundles" / "quick.bundle").read_bytes() == BIG, "CommonBundles в bundles, большой файл в несколько кусков")
    check(not (out / "quick.bundle").exists(), "quick.bundle не лежит в корне App")
    check((out / "graw2.exe").read_bytes() == FILES[7]["data"], "внешний файл найден в подпапках/в корне")
    check((out / "settings" / "hud.xml").read_bytes() == b"<hud/>", "CommonSettings в settings")
    check(not (out / "corecomp.ini").exists(), "файлы служебной группы <Support> не извлекаются")
    check((out / "_redist" / "PhysX_Setup.exe").is_file(), "redist")
    check(not (out / "InstallerUtil.dll").exists() and not (out / "Reader.exe").exists()
          and not (out / "setup.inx").exists(), "лишнего нет")

    # --- повреждение данных ловится по MD5, недописанный файл удаляется
    raw = bytearray((disc / "data2.cab").read_bytes())
    e = cab.entries[2]
    raw[e.doff + 8] ^= 0xFF
    (disc / "data2.cab").write_bytes(bytes(raw))
    try:
        cab.extract(e, t / "bad" / "x.bik"); check(False, "порча не замечена")
    except I.ISCError as err:
        check(True, "")
    check(not (t / "bad" / "x.bik").exists(), "недописанный файл удалён")
    count2, _, errs2 = I.extract_game(cab, t / "App2", "en", lambda *_: None)
    check(len(errs2) == 1 and "ESRB.bik" in errs2[0] and count2 == 4, f"порча одного файла: {errs2}")

    # --- нет тома / нет внешнего файла
    disc2 = t / "disc2"; disc2.mkdir()
    build(disc2, DIRS, FILES, GROUPS)
    os.remove(disc2 / "data2.cab")
    try:
        I.extract_game(I.open_cabinet(disc2 / "data1.hdr"), t / "A3", "en", lambda *_: None); check(False, "нет data2")
    except I.ISCError as err:
        check("data2.cab" in str(err), f"сообщение: {err}")
    disc3 = t / "disc3"; disc3.mkdir()
    build(disc3, DIRS, FILES, GROUPS)
    try:
        I.extract_game(I.open_cabinet(disc3 / "data1.hdr"), t / "A4", "en", lambda *_: None); check(False, "нет внешних")
    except I.ISCError as err:
        check("graw2.exe" in str(err) and "целиком" in str(err), f"сообщение: {err}")

    # --- версии и мусор
    bad = bytearray((disc / "data1.hdr").read_bytes()); struct.pack_into("<I", bad, 4, 0x02000000 + 1700)
    try:
        I.Cabinet(bytes(bad), disc); check(False, "версия 17")
    except I.ISCError as err:
        check("17" in str(err), "версия 17 не поддерживается")
    try:
        I.Cabinet(b"\0" * 0x300, disc); check(False, "не ISc")
    except I.ISCError:
        check(True, "")
    check(I.major_version(0x020004B0) == 12 and I.major_version(0x01006000) == 6, "major_version")

    # --- интеграция в Portabilizer
    check(P.detect_type(disc / "setup.exe") == "installshield", "detect_type exe")
    check(P.detect_type(disc / "data1.hdr") == "installshield", "detect_type hdr")
    check(P.find_installshield(t) == disc / "setup.exe", "find_installshield по папке")
    check(P.find_installer(t) == disc / "setup.exe", "find_installer видит InstallShield")
    P.EXTRACT_WARNINGS.clear(); P.ISC_NOTES.clear()
    app = t / "AppP"; logs.clear()
    check(P.extract(disc / "setup.exe", "installshield", app, logs.append) is False, "порча (ESRB.bik) = не успех")
    os.remove(disc / "data2.cab")
    build(disc, DIRS, FILES, GROUPS)
    (disc / "graw2.exe").write_bytes(FILES[7]["data"])
    P.EXTRACT_WARNINGS.clear(); P.ISC_NOTES.clear()
    ok = P.extract(disc / "setup.exe", "installshield", t / "AppQ", logs.append)
    check(ok is True, "полный диск: успех")
    check(any("перенесена только игра" in w for w in P.EXTRACT_WARNINGS), "R не удалит диск")
    check(any("_redist" in x for x in P.ISC_NOTES), "заметка про redist")
    check(P.find_main_exe(t / "AppQ") == (t / "AppQ" / "graw2.exe").resolve() or
          P.find_main_exe(t / "AppQ").name == "graw2.exe", "главный exe graw2.exe")

print(f"InstallShield: {n} проверок пройдено")
