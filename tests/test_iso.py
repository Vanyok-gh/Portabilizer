"""Сборка ISO: проверка отдельным читателем образа (читает и ISO 9660, и Joliet) и командой file.
Запуск: python tests/test_iso.py"""
import hashlib, os, random, struct, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pzp_iso as I

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

def rec_at(buf, o):
    ln = buf[o]
    if ln == 0: return None
    ext = struct.unpack_from("<I", buf, o + 2)[0]; ext_b = struct.unpack_from(">I", buf, o + 6)[0]
    size = struct.unpack_from("<I", buf, o + 10)[0]; size_b = struct.unpack_from(">I", buf, o + 14)[0]
    assert ext == ext_b and size == size_b, "числа в записи каталога не парные"
    fl = buf[o + 25]; nl = buf[o + 32]; ident = bytes(buf[o + 33:o + 33 + nl])
    assert ln % 2 == 0 and ln >= 33 + nl, "длина записи"
    return ln, ext, size, fl, ident

def read_dir(iso, ext, size, joliet):
    out, data = [], iso[ext * 2048: ext * 2048 + size]
    for s in range(0, size, 2048):
        sec, o = data[s:s + 2048], 0
        while o < 2048:
            r = rec_at(sec, o)
            if r is None: break
            ln, e, sz, fl, ident = r
            if ident not in (b"\0", b"\x01"):
                name = ident.decode("utf-16-be") if joliet else ident.decode("ascii").split(";")[0]
                out.append((name, e, sz, bool(fl & 2)))
            o += ln
    return out

def walk(iso, ext, size, joliet, prefix=""):
    res = {}
    for name, e, sz, isd in read_dir(iso, ext, size, joliet):
        if isd:
            res[prefix + name + "/"] = (e, sz)
            res.update(walk(iso, e, sz, joliet, prefix + name + "/"))
        else:
            res[prefix + name] = (e, sz)
    return res

def verify(src, isop, label):
    iso = Path(isop).read_bytes()
    check(len(iso) % 2048 == 0, "размер образа кратен сектору")
    for off, kind in ((16 * 2048, 1), (17 * 2048, 2)):
        d = iso[off:off + 2048]
        check(d[0] == kind and d[1:6] == b"CD001" and d[6] == 1, f"описатель тома типа {kind}")
        check(struct.unpack_from("<I", d, 80)[0] == len(iso) // 2048 == struct.unpack_from(">I", d, 84)[0], "размер тома в секторах")
        check(struct.unpack_from("<H", d, 128)[0] == 2048, "размер блока")
    check(iso[18 * 2048] == 255 and iso[18 * 2048 + 1:18 * 2048 + 6] == b"CD001", "завершающий описатель")
    pvd, svd = iso[16 * 2048:17 * 2048], iso[17 * 2048:18 * 2048]
    check(pvd[40:72].decode().strip() == label.upper(), "метка тома в ISO 9660")
    check(svd[40:72].decode("utf-16-be").rstrip("\x00 ") == label and svd[88:91] == b"%/E", "метка и признак Joliet")
    def adj(name):                      # Joliet: имя не длиннее 64 символов, расширение сохраняется
        if len(name) <= 64: return name
        stem, _, ext = name.rpartition("."); return stem[:64 - len(ext) - 1] + "." + ext
    def adjpath(rel):
        parts = rel.split("/"); return "/".join(adj(x) if x else x for x in parts)
    srcfiles = {}
    for root, dirs, files in os.walk(src):
        for d in dirs: srcfiles[adjpath(os.path.relpath(os.path.join(root, d), src).replace(os.sep, "/")) + "/"] = None
        for f in files: srcfiles[adjpath(os.path.relpath(os.path.join(root, f), src).replace(os.sep, "/"))] = os.path.join(root, f)
    for off, joliet in ((156, True), (156, False)):
        d = svd if joliet else pvd
        ln, e, sz, fl, ident = rec_at(d, 156)
        check(fl & 2 and ident == b"\0", "корневая запись")
        tree = walk(iso, e, sz, joliet)
        if joliet:
            check(set(tree) == set(k for k in srcfiles), "Joliet: те же имена, что в исходной папке")
            for k, v in srcfiles.items():
                if v is None: continue
                ee, ss = tree[k]
                data = Path(v).read_bytes()
                check(ss == len(data), f"размер {k}")
                got = iso[ee * 2048: ee * 2048 + ss] if ss else b""
                check(hashlib.sha256(got).digest() == hashlib.sha256(data).digest(), f"содержимое {k}")
        else:
            check(len(tree) == len(srcfiles), "ISO 9660: столько же записей")
            check(all(len(x.rsplit("/", 2)[-2 if x.endswith("/") else -1].split(".")[0]) <= 8 for x in tree), "ISO 9660: имена 8.3")
        # таблицы путей
        ptsize = struct.unpack_from("<I", d, 132)[0]; lpt = struct.unpack_from("<I", d, 140)[0]; mpt = struct.unpack_from(">I", d, 148)[0]
        L, M = iso[lpt * 2048: lpt * 2048 + ptsize], iso[mpt * 2048: mpt * 2048 + ptsize]
        o, entries = 0, []
        while o < ptsize:
            li, _, ex, par = struct.unpack_from("<BBIH", L, o); entries.append((L[o + 8:o + 8 + li], ex, par)); o += 8 + li + (li % 2)
        o = 0
        for ident, ex, par in entries:
            li, _, exm, parm = struct.unpack_from(">BBIH", M, o); check((exm, parm) == (ex, par) and M[o + 8:o + 8 + li] == ident, "M-таблица зеркальна L-таблице"); o += 8 + li + (li % 2)
        dirs_found = sorted([e] + [v[0] for k, v in tree.items() if k.endswith("/")])
        check(sorted(x[1] for x in entries) == dirs_found, "таблица путей: те же каталоги, что в дереве")
        check(entries[0][2] == 1 and all(1 <= p <= len(entries) for _, _, p in entries), "родители в таблице путей")

tmp = Path(tempfile.mkdtemp()); src = tmp / "disc"
(src / "Data" / "Maps" / "CutScene").mkdir(parents=True); (src / "Data" / "Audio").mkdir(); (src / "Empty").mkdir()
rnd = random.Random(1)
def put(rel, size):
    p = src / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(rnd.randbytes(size))
put("Launcher.exe", 100000); put("AUTORUN.INF", 40); put("setup.exe", 71680)
put("Data/Maps/PARIS1.GMX.CLZ", 5 * 1024 * 1024 + 123); put("Data/Maps/CutScene/CS_1_22.GMX.CLZ", 2048); put("Data/Audio/paris1.AWD.CLZ", 300000)
put("Data/Audio/Файл на русском.txt", 10); put("Empty.dat", 0); put("README", 5)
put("LongFileName_one.txt", 7); put("LongFileName_two.txt", 7); put("LongFileName_three.txt", 7)
for i in range(300): put(f"Data/Many/файл_номер_{i:04d}_с_длинным_названием_для_проверки.bin", 100 + i)
put("n" * 100 + ".extension", 9)
iso = tmp / "TRAOD1.iso"
seen = []
size = I.build_iso(src, iso, "TRAOD1", progress=lambda d, t: seen.append((d, t)))
check(size == iso.stat().st_size and seen and seen[-1][0] == seen[-1][1], "размер и отчёт о ходе")
verify(src, iso, "TRAOD1")
out = subprocess.run(["file", "-b", str(iso)], capture_output=True, text=True).stdout
check("ISO 9660" in out and "TRAOD1" in out, "команда file узнаёт образ и метку: " + out.strip())
# ошибки и аккуратность
for bad in (lambda: I.build_iso(tmp / "нет", tmp / "a.iso", "X"), lambda: I.build_iso(src, tmp / "b.iso", ""),
            lambda: I.build_iso(src, tmp / "c.iso", "X" * 33), lambda: I.build_iso(src, src / "inside.iso", "X")):
    try: bad(); check(False, "ожидалась ошибка")
    except I.IsoError: check(True, "понятная ошибка")
check(not list(tmp.glob("*.part")) and not (src / "inside.iso").exists(), "после ошибки временных файлов нет")
try: I.build_iso(src, tmp / "stop.iso", "X", should_stop=lambda: True); check(False, "прерывание")
except I.IsoError: check(not (tmp / "stop.iso").exists() and not list(tmp.glob("*.part")), "прерванный образ удалён")
# пустая папка и повтор для идентичных входных данных
e = tmp / "empty"; e.mkdir(); I.build_iso(e, tmp / "e.iso", "EMPTY"); verify(e, tmp / "e.iso", "EMPTY")
I.build_iso(src, tmp / "again.iso", "TRAOD1", volume_time=1)
I.build_iso(src, tmp / "again2.iso", "TRAOD1", volume_time=1)
check((tmp / "again.iso").read_bytes() == (tmp / "again2.iso").read_bytes(), "одинаковый вход и время дают одинаковый образ")
print("сборка ISO:", n, "проверок пройдено")
