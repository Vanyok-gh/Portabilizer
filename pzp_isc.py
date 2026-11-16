"""Чтение InstallShield-кабинетов (setup.exe + data1.hdr + data1.cab, data2.cab ...) на чистом Python.

Формат версий 6-16 (InstallShield 6-2010, InstallScript). Установщик не запускается, права
администратора не нужны: файлы раскладываются по таблице кабинета, у каждого проверяется MD5.

Что внутри:
  - data1.hdr (или начало data1.cab, если заголовок встроен): таблица папок, файлов и групп файлов;
  - dataN.cab: данные файлов. Файл хранится кусками: 2 байта длины + сырой deflate (до 64 КБ после распаковки).

Что НЕ делается:
  - скрипт setup.inx зашифрован и не читается, поэтому куда установщик кладёт каждую группу, определяется
    по структуре папок кабинета (см. select_files);
  - файлы, разрезанные между томами, и «затуманенные» файлы (FILE_OBFUSCATED) не поддерживаются:
    при встрече выдаётся понятная ошибка, а не испорченный файл.
"""
import hashlib
import os
import re
import struct
import zlib
from pathlib import Path

SIGNATURE = 0x28635349          # "ISc("
FILE_SPLIT = 0x1
FILE_OBFUSCATED = 0x2
FILE_COMPRESSED = 0x4
FILE_INVALID = 0x8
DESC_SIZE = 0x57                # размер записи файла в версиях 6+
MAX_GROUPS = 71
ZERO_MD5 = b"\0" * 16


class ISCError(Exception):
    """Кабинет не читается или не поддерживается."""


class Entry:
    __slots__ = ("index", "flags", "size", "comp", "doff", "md5", "name", "dir", "volume")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    @property
    def relpath(self) -> str:
        return (self.dir + "\\" + self.name) if self.dir else self.name

    @property
    def valid(self) -> bool:
        return not (self.flags & FILE_INVALID) and bool(self.name) and "://" not in self.dir

    @property
    def loose(self) -> bool:
        """Файл лежит на диске отдельно от кабинета (внешний, не сжатый)."""
        return not (self.flags & FILE_COMPRESSED) and self.doff == 0


class Group:
    __slots__ = ("name", "first", "last")

    def __init__(self, name, first, last):
        self.name, self.first, self.last = name, first, last

    def __repr__(self):
        return f"Group({self.name!r}, {self.first}-{self.last})"


def major_version(ver: int) -> int:
    """Версия InstallShield из поля version заголовка (как у unshield)."""
    top = ver >> 24
    if top == 1:
        return (ver >> 12) & 0xF
    if top in (2, 4):
        major = ver & 0xFFFF
        return major // 100 if major else 0
    return 0


def _cstr(data: bytes, off: int) -> str:
    if off < 0 or off >= len(data):
        return ""
    end = data.find(b"\0", off)
    return data[off:end if end >= 0 else len(data)].decode("cp1252", "replace")


class Cabinet:
    """Таблица кабинета: файлы и группы. data1.hdr читается целиком в память (сотни КБ)."""

    def __init__(self, header: bytes, cab_dir: Path):
        self.cab_dir = Path(cab_dir)
        self.entries = []
        self.groups = []
        self._index = None              # имя файла (нижний регистр) -> пути на диске, строится при первой надобности
        self._parse(header)

    def _parse(self, h: bytes):
        if len(h) < 0x240:
            raise ISCError("заголовок InstallShield слишком короткий")
        sig, ver, _vol, desc, desc_size = struct.unpack_from("<5I", h, 0)
        if sig != SIGNATURE:
            raise ISCError("это не заголовок InstallShield (нет сигнатуры ISc()")
        self.major = major_version(ver)
        if self.major < 6 or self.major >= 17:
            raise ISCError(f"InstallShield {self.major or '?'} не поддерживается (нужны версии 6-16)")
        if desc == 0 or desc_size == 0 or desc + desc_size > len(h):
            raise ISCError("в заголовке нет таблицы файлов (нужен файл data1.hdr рядом с data1.cab)")
        u32 = lambda o: struct.unpack_from("<I", h, o)[0]
        u16 = lambda o: struct.unpack_from("<H", h, o)[0]
        table = desc + u32(desc + 0x0C)             # таблица смещений папок
        dirs_n = u32(desc + 0x1C)
        files_n = u32(desc + 0x28)
        recs = table + u32(desc + 0x2C)             # записи файлов (по DESC_SIZE байт)
        if recs + files_n * DESC_SIZE > len(h) or dirs_n > 100000 or files_n > 1000000:
            raise ISCError("таблица файлов InstallShield повреждена")
        dirs = [_cstr(h, table + u32(table + 4 * i)) for i in range(dirs_n)]
        for i in range(files_n):
            p = recs + i * DESC_SIZE
            di = u16(p + 62)
            self.entries.append(Entry(
                index=i, flags=u16(p), size=u32(p + 2), comp=u32(p + 10), doff=u32(p + 18),
                md5=bytes(h[p + 26:p + 42]), name=_cstr(h, table + u32(p + 58)),
                dir=dirs[di] if di < dirs_n else "", volume=u16(p + 85)))
        for i in range(MAX_GROUPS):                  # группы файлов: цепочки из записей по 12 байт
            off = u32(desc + 0x3E + 4 * i)
            seen = 0
            while off and seen < 1000:
                seen += 1
                if desc + off + 12 > len(h):
                    break
                name_off, g_off, nxt = struct.unpack_from("<3I", h, desc + off)
                g = desc + g_off
                if g + 0x1E <= len(h):
                    first, last = u32(g + 0x16), u32(g + 0x1A)
                    if first < files_n and last < files_n and first <= last:
                        self.groups.append(Group(_cstr(h, desc + name_off), first, last))
                off = nxt

    def group_files(self, group: Group):
        return self.entries[group.first:group.last + 1]

    # ------------------------------------------------------------------ чтение данных

    def volume_path(self, n: int) -> Path:
        for name in (f"data{n}.cab", f"Data{n}.cab", f"DATA{n}.CAB"):
            p = self.cab_dir / name
            if p.is_file():
                return p
        raise ISCError(f"нет файла data{n}.cab рядом с data1.cab ({self.cab_dir})")

    def check_volumes(self, entries):
        """Все тома, нужные файлам, есть и достаточно большие. Возвращает {номер: размер}."""
        need, sizes = {}, {}
        for e in entries:
            if e.loose:
                continue
            need[e.volume] = max(need.get(e.volume, 0), e.doff + e.comp)
        for n, end in need.items():
            p = self.volume_path(n)
            sizes[n] = p.stat().st_size
            if end > sizes[n]:
                raise ISCError(f"{p.name} короче, чем нужно ({sizes[n]} < {end} байт): "
                               "файл разрезан между томами или том скачан не полностью")
        return sizes

    def _disc_index(self):
        if self._index is None:
            self._index = {}
            base = str(self.cab_dir)
            for root, dirs, files in os.walk(base):
                if root[len(base):].count(os.sep) >= 4:
                    dirs[:] = []
                for name in files:
                    self._index.setdefault(name.lower(), []).append(os.path.join(root, name))
        return self._index

    def loose_path(self, e: Entry):
        """Внешний файл диска: рядом с кабинетом или в любой подпапке диска; размер должен совпасть."""
        for p in (self.cab_dir / e.dir / e.name, self.cab_dir / e.name):
            try:
                if p.is_file() and p.stat().st_size == e.size:
                    return p
            except OSError:
                pass
        for c in self._disc_index().get(e.name.lower(), []):
            try:
                if os.path.getsize(c) == e.size:
                    return Path(c)
            except OSError:
                pass
        return None

    def missing_loose(self, entries):
        """Внешние файлы диска, которых нет на месте (их данные не в кабинете)."""
        return [e for e in entries if e.loose and self.loose_path(e) is None]

    def extract(self, e: Entry, dest: Path, progress=None, verify=True):
        """Записывает файл в dest. progress(байты) вызывается по ходу записи. MD5 проверяется всегда,
        если он есть в таблице; при расхождении ISCError (недописанный файл удаляется)."""
        if e.flags & FILE_OBFUSCATED:
            raise ISCError(f"{e.relpath}: файл «затуманен» (FILE_OBFUSCATED), такие пока не поддерживаются")
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        md5 = hashlib.md5()
        done = 0
        try:
            with open(dest, "wb") as out:
                for chunk in self._chunks(e):
                    out.write(chunk)
                    md5.update(chunk)
                    done += len(chunk)
                    if progress:
                        progress(len(chunk))
            if done != e.size:
                raise ISCError(f"{e.relpath}: получено {done} байт вместо {e.size}")
            if verify and e.md5 != ZERO_MD5 and md5.digest() != e.md5:
                raise ISCError(f"{e.relpath}: контрольная сумма MD5 не совпала (том повреждён?)")
        except BaseException:
            try:
                dest.unlink()
            except OSError:
                pass
            raise

    def _chunks(self, e: Entry):
        if e.loose:
            src = self.loose_path(e)
            if not src:
                raise ISCError(f"{e.relpath}: внешний файл не найден рядом с кабинетом")
            with open(src, "rb") as f:
                while True:
                    b = f.read(1 << 20)
                    if not b:
                        return
                    yield b
        with open(self.volume_path(e.volume), "rb") as f:
            f.seek(e.doff)
            left = e.comp
            if not (e.flags & FILE_COMPRESSED):
                while left > 0:
                    b = f.read(min(left, 1 << 20))
                    if not b:
                        raise ISCError(f"{e.relpath}: неожиданный конец тома")
                    left -= len(b)
                    yield b
                return
            while left > 0:
                head = f.read(2)
                if len(head) < 2:
                    raise ISCError(f"{e.relpath}: неожиданный конец тома")
                n = struct.unpack("<H", head)[0]
                left -= 2 + n
                if n == 0 or left < 0:
                    raise ISCError(f"{e.relpath}: повреждён блок данных")
                block = f.read(n)
                if len(block) < n:
                    raise ISCError(f"{e.relpath}: неожиданный конец тома")
                try:
                    yield zlib.decompressobj(-15).decompress(block + b"\0")   # нулевой байт, как в unshield
                except zlib.error as err:
                    raise ISCError(f"{e.relpath}: ошибка распаковки ({err})")


# ---------------------------------------------------------------------- открытие

def find_cabinet_files(path) -> tuple:
    """path: setup.exe, data1.hdr, data1.cab или папка диска. Возвращает (hdr_или_cab, папка_кабинетов)
    либо (None, None), если InstallShield-кабинета рядом нет."""
    p = Path(path)
    folder = p if p.is_dir() else p.parent
    for name in ("data1.hdr", "Data1.hdr", "DATA1.HDR", "data1.cab", "Data1.cab", "DATA1.CAB"):
        c = folder / name
        if c.is_file():
            try:
                with open(c, "rb") as f:
                    if f.read(4) == struct.pack("<I", SIGNATURE):
                        return c, folder
            except OSError:
                pass
    return None, None


def looks_like_installshield(path) -> bool:
    """Быстрая проверка для detect_type: рядом лежит кабинет InstallShield с сигнатурой ISc(."""
    try:
        hdr, _ = find_cabinet_files(path)
    except OSError:
        return False
    return hdr is not None


def open_cabinet(path) -> Cabinet:
    hdr, folder = find_cabinet_files(path)
    if hdr is None:
        raise ISCError("рядом нет data1.hdr / data1.cab InstallShield")
    data = hdr.read_bytes() if hdr.suffix.lower() == ".hdr" else _embedded_header(hdr)
    return Cabinet(data, folder)


def _embedded_header(cab: Path) -> bytes:
    with open(cab, "rb") as f:
        head = f.read(20)
        _sig, _ver, _vol, desc, desc_size = struct.unpack("<5I", head)
        if not desc_size:
            raise ISCError("в data1.cab нет заголовка: положите рядом data1.hdr")
        f.seek(0)
        return f.read(desc + desc_size)


# ---------------------------------------------------------------------- выбор файлов игры

# суффиксы языковых групп и их английские эквиваленты
LANG_SETS = {
    "en": ("UK", "US", "EN", "ENG"), "fr": ("FR", "FRA"), "de": ("GER", "DE", "DEU"),
    "it": ("IT", "ITA"), "es": ("SP", "ES", "ESP"), "ru": ("RU", "RUS"), "pl": ("PL", "POL"),
    "cs": ("CZ", "CS", "CZE"), "hu": ("HU", "HUN"), "nl": ("NL", "DU", "DUT"),
    "sv": ("SE", "SV", "SWE"), "da": ("DK", "DA", "DAN"), "pt": ("PT", "BR", "POR"),
}
_ALL_LANG_SUFFIXES = sorted({s for v in LANG_SETS.values() for s in v}, key=len, reverse=True)
_LANG_GROUP = re.compile(r"^(?P<fam>[A-Za-z]+?)(?P<suf>" + "|".join(_ALL_LANG_SUFFIXES) + r")$", re.I)

# группы-установщики и вспомогательные программы: в портативную папку не нужны
_SKIP_GROUPS = re.compile(
    r"^(directx|dx\b|dxsetup|acrobat|adobe|reader|ageia|physx|vcredist|vc\d|dotnet|\.net|teamspeak|"
    r"register|gamespy|detection|md5|manual|redist|commondll|commonmce)", re.I)
_SKIP_FILES = re.compile(r"(?i)(installerutil|installhelper|instancechecker|unins|^setup\.|^_setup|\.inx$)")
# группы, которые установщик кладёт в подпапку (определено по структуре кабинета: папка есть, но пуста)
_GROUP_SUBDIR = {"commonsettings": "settings"}
# программы, которые полезно сохранить отдельно (ставятся один раз вручную)
_REDIST_GROUPS = re.compile(r"^(ageia|physx)", re.I)


def language_of(name: str):
    """('Data', 'FR') для группы DataFR, иначе None."""
    m = _LANG_GROUP.match(name)
    return (m.group("fam"), m.group("suf")) if m else None


def select_files(cab: Cabinet, language: str = "en"):
    """Файлы игры для портативной папки.

    Возвращает (files, redist, skipped): files - список (Entry, относительный путь),
    redist - то же для установщиков вроде PhysX (кладутся в _redist), skipped - [(группа, число файлов)]."""
    want = LANG_SETS.get(language.lower(), (language.upper(),))
    families = {}
    for g in cab.groups:
        lg = language_of(g.name)
        if lg and not g.name.startswith("<"):
            families.setdefault(lg[0].lower(), []).append(g)
    files, redist, skipped, seen = [], [], [], {}
    for g in cab.groups:
        name = g.name
        entries = [e for e in cab.group_files(g) if e.valid]
        if not entries:
            continue
        if name.startswith("<") or _SKIP_GROUPS.match(name):
            if _REDIST_GROUPS.match(name):
                redist.extend((e, e.name) for e in entries)
            skipped.append((name, len(entries)))
            continue
        lg = language_of(name)
        if lg and len(families.get(lg[0].lower(), [])) > 1 and lg[1].upper() not in want:
            skipped.append((name, len(entries)))
            continue
        sub = _GROUP_SUBDIR.get(name.lower(), "")
        for e in entries:
            if _SKIP_FILES.search(e.name):
                continue
            rel = (sub + "\\" if sub else "") + e.relpath
            if ".." in rel.replace("\\", "/").split("/") or ":" in rel or rel.startswith(("/", "\\")):
                continue                                  # путь вне папки игры: такие записи не извлекаем
            files.append((e, rel.replace("\\", os.sep)))
    out = []
    for e, rel in files:                              # одинаковый путь из разных групп: берём последний
        seen[rel.lower()] = (e, rel)
    out = list(seen.values())
    return out, redist, skipped


def extract_game(cab: Cabinet, dest, language="en", log=print, progress=None, cancelled=None):
    """Раскладывает файлы игры в dest. Возвращает (число файлов, байт, список ошибок).
    progress(доля 0..1), cancelled() -> bool для прерывания."""
    dest = Path(dest)
    files, redist, skipped = select_files(cab, language)
    if not files:
        raise ISCError("в кабинете не нашлось файлов игры")
    cab.check_volumes([e for e, _ in files + redist])
    absent = cab.missing_loose([e for e, _ in files])
    if absent:
        names = ", ".join(e.relpath for e in absent[:6]) + (" ..." if len(absent) > 6 else "")
        raise ISCError(f"на диске нет файлов, которые лежат отдельно от кабинета ({len(absent)}): {names}. "
                       "Скопируйте весь диск целиком, а не только data1.cab и data2.cab")
    redist = [(e, r) for e, r in redist if cab.loose_path(e) or not e.loose]
    total = sum(e.size for e, _ in files + redist) or 1
    state = {"done": 0}

    def tick(n):
        state["done"] += n
        if progress:
            progress(min(1.0, state["done"] / total))
        if cancelled and cancelled():
            raise ISCError("прервано")

    errors, count, size = [], 0, 0
    log(f"InstallShield {cab.major}: файлов игры {len(files)}, "
        f"{sum(e.size for e, _ in files) / 1048576:.0f} МБ; пропущены группы установщика: "
        + (", ".join(f"{n} ({c})" for n, c in skipped) or "нет"))
    for e, rel in files:
        try:
            cab.extract(e, dest / rel, progress=tick)
            count += 1
            size += e.size
        except ISCError as err:
            if str(err) == "прервано":
                raise
            errors.append(str(err))
            log("Ошибка: " + str(err))
    if redist:
        for e, rel in redist:
            try:
                cab.extract(e, dest / "_redist" / rel, progress=tick)
            except ISCError as err:
                log("Ошибка: " + str(err))
    return count, size, errors
