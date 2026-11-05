"""Сборка образа диска ISO 9660 (+ Joliet) из папки. Только стандартная библиотека.

Нужна, чтобы игра, проверяющая «диск с такой-то меткой в приводе», увидела настоящий CD-привод: образ
подключается средствами Windows (Mount-DiskImage), в проводнике он выглядит как DVD-привод с нужной меткой.

Формат написан по открытым описаниям ECMA-119 (ISO 9660) и Joliet (UCS-2, имена до 64 символов); файлы
UltraISO и других программ не используются. Поддержано: каталоги любой глубины, длинные имена и юникод
(Joliet), метка тома, отдельные файлы до 4 ГБ. Не поддержано: загрузочные образы, UDF, многосекционные
файлы больше 4 ГБ (выдаётся понятная ошибка).
"""
from __future__ import annotations

import os
import re
import struct
import time
from pathlib import Path

SECTOR = 2048
MAX_FILE = (1 << 32) - SECTOR            # ограничение одного экстента ISO 9660
JOLIET_MAX = 64                          # длина имени в Joliet (символов)


class IsoError(Exception):
    pass


# ---------------------------------------------------------------- вспомогательное
def _both32(v):
    return struct.pack("<I", v) + struct.pack(">I", v)


def _both16(v):
    return struct.pack("<H", v) + struct.pack(">H", v)


def _date7(t):
    g = time.gmtime(t)
    return bytes([g.tm_year - 1900, g.tm_mon, g.tm_mday, g.tm_hour, g.tm_min, g.tm_sec, 0])


def _date17(t):
    g = time.gmtime(t)
    return (time.strftime("%Y%m%d%H%M%S", g) + "00").encode("ascii") + b"\0"


def _pad(b, n, fill=b" "):
    return (b + fill * n)[:n]


def _dchars(s, maxlen):
    s = re.sub(r"[^A-Z0-9_]", "_", s.upper())
    return s[:maxlen]


def _iso_names(names, is_dir):
    """Короткие уникальные имена 8.3 для ISO 9660 (Windows при наличии Joliet читает длинные)."""
    out, used = {}, set()
    for name in names:
        if is_dir[name]:
            base, ext = _dchars(name, 8) or "_", ""
        else:
            stem, dot, e = name.rpartition(".")
            stem, e = (stem, e) if dot and stem else (name, "")
            base, ext = _dchars(stem, 8) or "_", _dchars(e, 3)
        n, cand = 0, None
        while True:
            suf = "" if n == 0 else "~%d" % n
            cand_base = base[:8 - len(suf)] + suf
            cand = cand_base + ("." + ext if ext else "")
            if cand not in used:
                break
            n += 1
        used.add(cand)
        out[name] = cand
    return out


def _joliet_name(name, used):
    s = re.sub(r'[\x00-\x1f*/:;?\\]', "_", name)
    if len(s) > JOLIET_MAX:
        stem, dot, ext = s.rpartition(".")
        if dot and 0 < len(ext) <= 10:
            s = stem[:JOLIET_MAX - len(ext) - 1] + "." + ext
        else:
            s = s[:JOLIET_MAX]
    base, n = s, 1
    while s.lower() in used:
        suf = "~%d" % n
        stem, dot, ext = base.rpartition(".")
        s = (stem[:JOLIET_MAX - len(suf) - len(ext) - 1] + suf + "." + ext) if dot and stem else base[:JOLIET_MAX - len(suf)] + suf
        n += 1
    used.add(s.lower())
    return s


class _Node:
    __slots__ = ("name", "path", "is_dir", "size", "mtime", "children", "parent", "iso", "jol", "lba", "dsize", "num")

    def __init__(self, name, path, is_dir, size, mtime, parent):
        self.name, self.path, self.is_dir, self.size, self.mtime, self.parent = name, path, is_dir, size, mtime, parent
        self.children, self.iso, self.jol, self.lba, self.dsize, self.num = [], "", "", 0, 0, 0


def _scan(root: Path):
    top = _Node("", root, True, 0, root.stat().st_mtime, None)
    stack = [top]
    while stack:
        node = stack.pop()
        try:
            entries = sorted(os.scandir(node.path), key=lambda e: e.name.lower())
        except OSError as e:
            raise IsoError(f"Не удалось прочитать папку {node.path}: {e}")
        for e in entries:
            if e.is_symlink():
                continue
            if e.is_dir(follow_symlinks=False):
                ch = _Node(e.name, Path(e.path), True, 0, e.stat().st_mtime, node)
                node.children.append(ch)
                stack.append(ch)
            elif e.is_file(follow_symlinks=False):
                st = e.stat()
                if st.st_size >= MAX_FILE:
                    raise IsoError(f"Файл {e.path} больше 4 ГБ: формат ISO 9660 такое не вмещает.")
                node.children.append(_Node(e.name, Path(e.path), False, st.st_size, st.st_mtime, node))
    return top


def _assign_names(node):
    is_dir = {c.name: c.is_dir for c in node.children}
    iso = _iso_names([c.name for c in node.children], is_dir)
    used = set()
    for c in node.children:
        c.iso = iso[c.name]
        c.jol = _joliet_name(c.name, used)
        if c.is_dir:
            _assign_names(c)


def _record(extent, size, mtime, flags, ident: bytes):
    n = len(ident)
    rec = (bytes([0, 0]) + _both32(extent) + _both32(size) + _date7(mtime) + bytes([flags, 0, 0]) + _both16(1)
           + bytes([n]) + ident)
    if len(rec) % 2:
        rec += b"\0"
    return bytes([len(rec)]) + rec[1:]


def _ident(node, joliet):
    if joliet:
        return node.jol.encode("utf-16-be")
    return (node.iso if node.is_dir else node.iso + ";1").encode("ascii")


def _sorted_children(node, joliet):
    if joliet:
        return sorted(node.children, key=lambda c: c.jol.encode("utf-16-be"))
    return sorted(node.children, key=lambda c: (_ident(c, False)))


def _dir_extent(node, parent, joliet, mtime):
    """Содержимое каталога: записи не пересекают границу сектора."""
    recs = [_record(node.lba, node.dsize, node.mtime, 2, b"\0"),
            _record(parent.lba, parent.dsize, parent.mtime, 2, b"\x01")]
    for c in _sorted_children(node, joliet):
        recs.append(_record(c.lba, c.dsize if c.is_dir else c.size, c.mtime, 2 if c.is_dir else 0, _ident(c, joliet)))
    out, cur = [], b""
    for r in recs:
        if len(cur) + len(r) > SECTOR:
            out.append(cur.ljust(SECTOR, b"\0"))
            cur = b""
        cur += r
    out.append(cur.ljust(SECTOR, b"\0"))
    return b"".join(out)


def _dir_size(node, joliet):
    n_sec, cur = 1, 34 + 34
    for c in _sorted_children(node, joliet):
        ln = 33 + len(_ident(c, joliet))
        ln += ln % 2
        if cur + ln > SECTOR:
            n_sec, cur = n_sec + 1, 0
        cur += ln
    return n_sec * SECTOR


def _dirs_bfs(top, joliet):
    order, queue = [], [top]
    while queue:
        d = queue.pop(0)
        order.append(d)
        queue += [c for c in _sorted_children(d, joliet) if c.is_dir]
    return order


def _path_table(order, joliet, little):
    index = {id(d): i + 1 for i, d in enumerate(order)}
    out = b""
    for i, d in enumerate(order):
        ident = b"\0" if d.parent is None else _ident(d, joliet)
        parent = 1 if d.parent is None else index[id(d.parent)]
        lba = struct.pack("<I" if little else ">I", d.lba)
        par = struct.pack("<H" if little else ">H", parent)
        rec = bytes([len(ident), 0]) + lba + par + ident
        if len(ident) % 2:
            rec += b"\0"
        out += rec
    return out


def _descriptor(kind, label, total, pt_size, lpt, mpt, root_rec, t, joliet):
    d = bytearray(SECTOR)
    d[0] = 2 if joliet else 1
    d[1:6] = b"CD001"
    d[6] = 1
    enc = (lambda s, n: s.encode("utf-16-be").ljust(n, b"\0")[:n]) if joliet else (lambda s, n: _pad(s.encode("ascii", "replace"), n))
    blank = (lambda n: (b"\0\x20" * n)[:n]) if joliet else (lambda n: b" " * n)
    d[8:40] = enc("", 32) if not joliet else blank(32)
    lab = label if joliet else _dchars(label, 32)
    d[40:72] = _pad(lab.encode("utf-16-be"), 32, b"\0\x20") if joliet else _pad(lab.encode("ascii"), 32)
    d[80:88] = _both32(total)
    if joliet:
        d[88:91] = b"%/E"
    d[120:124] = _both16(1)
    d[124:128] = _both16(1)
    d[128:132] = _both16(SECTOR)
    d[132:140] = _both32(pt_size)
    d[140:144] = struct.pack("<I", lpt)
    d[148:152] = struct.pack(">I", mpt)
    d[156:190] = root_rec
    for off, n in ((190, 128), (318, 128), (446, 128), (574, 128)):
        d[off:off + n] = blank(n)
    for off in (702, 739, 776):
        d[off:off + 37] = blank(37)
    d[813:830] = _date17(t)
    d[830:847] = _date17(t)
    d[847:864] = b"0" * 16 + b"\0"
    d[864:881] = b"0" * 16 + b"\0"
    d[881] = 1
    assert len(d) == SECTOR, "описатель тома нарушил размер сектора"
    return bytes(d)


# ---------------------------------------------------------------- главная функция
def build_iso(src, out, label, progress=None, volume_time=None, should_stop=None):
    """Собирает ISO из папки src в файл out с меткой тома label (до 32 символов).

    progress(done_bytes, total_bytes) - необязательный отчёт о ходе; should_stop() -> True прерывает
    работу (частично записанный файл удаляется). Возвращает размер образа в байтах."""
    src, out = Path(src), Path(out)
    if not src.is_dir():
        raise IsoError(f"Папка не найдена: {src}")
    label = str(label or "").strip()
    if not label or len(label) > 32:
        raise IsoError("Метка тома должна быть от 1 до 32 символов.")
    try:
        if out.resolve().is_relative_to(src.resolve()):
            raise IsoError("Файл образа нельзя сохранять внутри папки, из которой он собирается.")
    except (OSError, ValueError):
        pass
    t = volume_time or time.time()
    top = _scan(src)
    _assign_names(top)

    def all_dirs():
        r, st = [], [top]
        while st:
            d = st.pop(); r.append(d); st += [c for c in d.children if c.is_dir]
        return r

    def all_files():
        r, st = [], [top]
        while st:
            d = st.pop()
            r += [c for c in _sorted_children(d, False) if not c.is_dir]
            st += [c for c in d.children if c.is_dir]
        return r
    dirs, files = all_dirs(), all_files()
    ob_i, ob_j = _dirs_bfs(top, False), _dirs_bfs(top, True)

    pt_i = len(_path_table(ob_i, False, True))
    pt_j = len(_path_table(ob_j, True, True))
    sec = lambda n: (n + SECTOR - 1) // SECTOR                                     # noqa: E731
    lba = 19
    lpt_i = lba; lba += sec(pt_i)
    mpt_i = lba; lba += sec(pt_i)
    lpt_j = lba; lba += sec(pt_j)
    mpt_j = lba; lba += sec(pt_j)
    # каталоги: у каждого узла две «копии» (ISO и Joliet) разного размера
    iso_ext, jol_ext = {}, {}
    for d in dirs:
        iso_ext[id(d)] = _dir_size(d, False)
        jol_ext[id(d)] = _dir_size(d, True)
    iso_lba, jol_lba = {}, {}
    for d in ob_i:
        iso_lba[id(d)] = lba; lba += iso_ext[id(d)] // SECTOR
    for d in ob_j:
        jol_lba[id(d)] = lba; lba += jol_ext[id(d)] // SECTOR
    for f in files:
        f.lba = lba if f.size else 0
        lba += sec(f.size)
    total_sectors = lba
    total_bytes = sum(f.size for f in files)

    def with_tree(joliet):
        lbas, sizes = (jol_lba, jol_ext) if joliet else (iso_lba, iso_ext)
        for d in dirs:
            d.lba, d.dsize = lbas[id(d)], sizes[id(d)]

    done = 0
    tmp = out.with_name(out.name + ".part")
    try:
        with open(tmp, "wb") as fo:
            fo.write(b"\0" * (16 * SECTOR))
            with_tree(False)
            root_i = _record(top.lba, top.dsize, top.mtime, 2, b"\0")
            pt_il, pt_im = _path_table(ob_i, False, True), _path_table(ob_i, False, False)
            with_tree(True)
            root_j = _record(top.lba, top.dsize, top.mtime, 2, b"\0")
            pt_jl, pt_jm = _path_table(ob_j, True, True), _path_table(ob_j, True, False)
            fo.write(_descriptor(1, label, total_sectors, pt_i, lpt_i, mpt_i, root_i, t, False))
            fo.write(_descriptor(2, label, total_sectors, pt_j, lpt_j, mpt_j, root_j, t, True))
            fo.write(b"\xff" + b"CD001" + b"\x01" + b"\0" * (SECTOR - 7))
            for blob in (pt_il, pt_im, pt_jl, pt_jm):
                fo.write(blob.ljust(sec(len(blob)) * SECTOR, b"\0"))
            with_tree(False)
            for d in ob_i:
                fo.write(_dir_extent(d, d.parent or d, False, t))
            with_tree(True)
            for d in ob_j:
                fo.write(_dir_extent(d, d.parent or d, True, t))
            # lba файлов не зависит от дерева; пишем в порядке выделения
            for f in files:
                if should_stop and should_stop():
                    raise IsoError("Прервано.")
                if not f.size:
                    continue
                with open(f.path, "rb") as fi:
                    left = f.size
                    while left:
                        chunk = fi.read(min(1 << 20, left))
                        if not chunk:
                            raise IsoError(f"Файл изменился во время записи: {f.path}")
                        fo.write(chunk)
                        left -= len(chunk)
                        done += len(chunk)
                        if progress:
                            progress(done, total_bytes)
                pad = -f.size % SECTOR
                if pad:
                    fo.write(b"\0" * pad)
        os.replace(tmp, out)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    return total_sectors * SECTOR


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Использование: python pzp_iso.py ПАПКА ОБРАЗ.iso МЕТКА_ТОМА")
        raise SystemExit(2)
    last = [-1]

    def show(d, t):
        p = int(100 * d / t) if t else 100
        if p != last[0]:
            last[0] = p
            print(f"\r{p}%", end="", flush=True)
    try:
        size = build_iso(sys.argv[1], sys.argv[2], sys.argv[3], show)
    except IsoError as e:
        print("\nОшибка:", e)
        raise SystemExit(1)
    print(f"\nГотово: {sys.argv[2]} ({size / 1048576:.1f} МБ)")
