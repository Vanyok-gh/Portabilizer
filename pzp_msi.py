"""Чтение таблиц MSI (OLE2 + Windows Installer) без внешних библиотек и без прав администратора.

Нужно, чтобы заранее узнать, каких исходных файлов (несжатых, лежащих рядом с msi на диске) не хватает:
msiexec /a падает на первом же отсутствующем файле, а нам нужно распаковать всё, что есть.
Только чтение; любые ошибки разбора вызывающий код должен считать «не знаю» и работать дальше.
"""
import struct
from pathlib import Path

MIME = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz._"

def dec_name(name):
    out = []
    for ch in name:
        c = ord(ch)
        if 0x3800 <= c < 0x4800:
            c -= 0x3800; out.append(MIME[c & 0x3f]); out.append(MIME[(c >> 6) & 0x3f])
        elif 0x4800 <= c < 0x4840:
            out.append(MIME[c - 0x4800])
        elif c == 0x4840:
            out.append("!")
        else:
            out.append(ch)
    return "".join(out)

class CFB:
    def __init__(self, data):
        self.d = data
        h = data[:512]
        assert h[:8] == bytes.fromhex("d0cf11e0a1b11ae1"), "не OLE2"
        self.ss = 1 << struct.unpack_from("<H", h, 0x1E)[0]
        self.mss = 1 << struct.unpack_from("<H", h, 0x20)[0]
        nfat, dirstart, self.cutoff, mfstart, nmf, difstart, ndif = struct.unpack_from("<IIIIIII", h, 0x2C)[0], struct.unpack_from("<I", h, 0x30)[0], struct.unpack_from("<I", h, 0x38)[0], struct.unpack_from("<I", h, 0x3C)[0], struct.unpack_from("<I", h, 0x40)[0], struct.unpack_from("<I", h, 0x44)[0], struct.unpack_from("<I", h, 0x48)[0]
        difat = list(struct.unpack_from("<109I", h, 0x4C))
        s = difstart
        for _ in range(ndif):
            sec = self.sector(s); vals = struct.unpack("<%dI" % (self.ss // 4), sec)
            difat += vals[:-1]; s = vals[-1]
        self.fat = []
        for s in difat[:nfat]:
            if s < 0xFFFFFFFA: self.fat += struct.unpack("<%dI" % (self.ss // 4), self.sector(s))
        self.dir = self.chain(dirstart)
        self.ents = []
        for i in range(len(self.dir) // 128):
            e = self.dir[i * 128:(i + 1) * 128]
            nl = struct.unpack_from("<H", e, 64)[0]
            name = e[:max(nl - 2, 0)].decode("utf-16le")
            typ = e[66]; start = struct.unpack_from("<I", e, 116)[0]; size = struct.unpack_from("<Q", e, 120)[0] & 0xFFFFFFFF
            self.ents.append((name, typ, start, size))
        self.root = self.ents[0]
        self.ministream = self.chain(self.root[2]) if self.root[2] < 0xFFFFFFFA else b""
        self.minifat = []
        if mfstart < 0xFFFFFFFA:
            mf = self.chain(mfstart); self.minifat = list(struct.unpack("<%dI" % (len(mf) // 4), mf))
    def sector(self, n): o = 512 + n * self.ss; return self.d[o:o + self.ss]
    def chain(self, s):
        out = []; seen = 0
        while s < 0xFFFFFFFA and seen < 1 << 22:
            out.append(self.sector(s)); s = self.fat[s]; seen += 1
        return b"".join(out)
    def stream(self, ent):
        name, typ, start, size = ent
        if size < self.cutoff:
            out = []; s = start
            while s < 0xFFFFFFFA:
                out.append(self.ministream[s * self.mss:(s + 1) * self.mss]); s = self.minifat[s]
            return b"".join(out)[:size]
        return self.chain(start)[:size]

class MSI:
    def __init__(self, path):
        self.c = CFB(open(path, "rb").read())
        self.streams = {dec_name(e[0]): e for e in self.c.ents if e[1] == 2}
        pool = self.get("!_StringPool"); data = self.get("!_StringData")
        hdr = struct.unpack_from("<I", pool, 0)[0]
        self.cp = (hdr & 0xFFFF) or 1252
        self.long = bool(hdr & 0x80000000)
        self.strs = [""]; pos = 0; i = 4
        while i + 4 <= len(pool):
            ln, rc = struct.unpack_from("<HH", pool, i); i += 4
            raw = data[pos:pos + ln]; pos += ln
            self.strs.append(raw.decode("cp%d" % self.cp if self.cp not in (0, 65001) else "utf-8", "replace"))
        self.rs = 3 if self.long else 2
        cols = self.rows_raw("_Columns", [("s", 0), ("i", 2), ("s", 0), ("i", 2)])
        self.schema = {}
        for t, n, name, ty in cols:
            self.schema.setdefault(t, {})[n] = (name, ty)
    def get(self, n): return self.c.stream(self.streams[n])
    def sref(self, b, o):
        v = int.from_bytes(b[o:o + self.rs], "little"); return self.strs[v] if v < len(self.strs) else ""
    def rows_raw(self, table, spec):
        b = self.get("!" + table); w = [self.rs if k == "s" else (4 if k == "l" else 2) for k, _ in spec]
        rl = sum(w); n = len(b) // rl if rl else 0
        cols = []; off = 0
        for (k, _), cw in zip(spec, w):
            col = []
            for r in range(n):
                p = off + r * cw
                if k == "s": col.append(self.strs[int.from_bytes(b[p:p + cw], "little")] if int.from_bytes(b[p:p + cw], "little") < len(self.strs) else "")
                elif k == "l": col.append((int.from_bytes(b[p:p + 4], "little") ^ 0x80000000))
                else: col.append(int.from_bytes(b[p:p + 2], "little") - 0x8000)
            cols.append(col); off += cw * n
        return list(zip(*cols)) if cols else []
    def table(self, name):
        if "!" + name not in self.streams: return None, []
        sc = self.schema.get(name, {})
        spec, names = [], []
        for i in sorted(sc):
            nm, ty = sc[i]; ty &= 0xFFFF
            if ty & 0x0800: spec.append(("s", 0))
            else: spec.append(("l" if (ty & 0xFF) == 4 else "i", 0))
            names.append(nm)
        return names, self.rows_raw(name, spec)
    def names(self): return sorted(k[1:] for k in self.streams if k.startswith("!"))


def _src_name(default_dir: str) -> str:
    """Имя каталога-источника из DefaultDir вида 'цель|Длинное:источник|Длинное'."""
    part = default_dir.split(":", 1)[1] if ":" in default_dir else default_dir
    return part.split("|", 1)[-1]


def source_dirs(msi: "MSI", base: Path) -> dict:
    """Ключ каталога -> путь к его источнику на диске (корень TARGETDIR = папка с msi)."""
    _, rows = msi.table("Directory")
    info = {r[0]: (r[1], r[2]) for r in rows}
    out = {}

    def resolve(key, depth=0):
        if key in out:
            return out[key]
        parent, dd = info.get(key, ("", ""))
        if not parent or key == "TARGETDIR" or depth > 40:
            res = base
        else:
            name = _src_name(dd)
            up = resolve(parent, depth + 1)
            res = up if name in (".", "") else up / name
        out[key] = res
        return res

    for k in info:
        resolve(k)
    return out


def missing_source_files(msi_path) -> list:
    """Список (ключ_File, ожидаемый_путь) несжатых файлов, которых нет рядом с msi.

    Несжатый файл (атрибут 0x2000, либо носитель без cab) msiexec берёт прямо из папки-источника.
    Файлы внутри cab-ов здесь не проверяются.
    """
    msi_path = Path(msi_path)
    msi = MSI(str(msi_path))
    dirs = source_dirs(msi, msi_path.parent)
    _, comps = msi.table("Component")
    comp_dir = {c[0]: c[2] for c in comps}
    _, media = msi.table("Media")
    media = sorted((m[1], m[3]) for m in media)               # (LastSequence, Cabinet)

    def loose_by_media(seq):
        for last, cab in media:
            if seq <= last:
                return not cab
        return False

    _, files = msi.table("File")
    missing = []
    for key, comp, fname, _size, _ver, _lang, attr, seq in files:
        if attr & 0x2000:
            loose = True
        elif attr & 0x4000:
            loose = False
        else:
            loose = loose_by_media(seq)
        if not loose:
            continue
        d = dirs.get(comp_dir.get(comp, ""), msi_path.parent)
        path = d / fname.split("|", 1)[-1]
        if not path.exists():
            missing.append((key, str(path)))
    return missing
