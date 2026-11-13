"""Чтение cab: без сжатия, MSZIP и LZX (одна или несколько папок внутри одного файла cab)."""
import struct
import zlib

import pzp_lzx


class CabError(Exception):
    pass


def parse(data: bytes, base=0):
    """-> [(имя, байты)] всех файлов cab. base - смещение cab внутри data (для cab в составе exe)."""
    if data[base:base + 4] != b"MSCF":
        raise CabError("не cab")
    (_, cbcab, _, coff, _, vmin, vmaj, nfold, nfile, flags, _sid, _icab) = struct.unpack(
        "<IIIIIBBHHHHH", data[base + 4:base + 36])
    p = base + 36
    rh = rf = rd = 0
    if flags & 4:
        rh, rf, rd = struct.unpack("<HBB", data[p:p + 4])
        p += 4 + rh
    if flags & 1:
        for _ in range(2):
            p = data.index(b"\0", p) + 1
    if flags & 2:
        for _ in range(2):
            p = data.index(b"\0", p) + 1
    folders = []
    for _ in range(nfold):
        off, nblk, comp = struct.unpack("<IHH", data[p:p + 8])
        folders.append((base + off, nblk, comp))
        p += 8 + rf
    files = []
    p = base + coff
    for _ in range(nfile):
        size, off, fol, _d, _t, _a = struct.unpack("<IIHHHH", data[p:p + 16])
        p += 16
        e = data.index(b"\0", p)
        files.append((data[p:e].decode("cp437", "replace"), size, off, fol))
        p = e + 1
    stores = []
    for off, nblk, comp in folders:
        q = off
        blocks = []
        for _ in range(nblk):
            _ck, cb, cu = struct.unpack("<IHH", data[q:q + 8])
            q += 8 + rd
            blocks.append((data[q:q + cb], cu))
            q += cb
        kind = comp & 15
        if kind == 0:
            stores.append(b"".join(b for b, _ in blocks))
        elif kind == 1:
            out, prev = [], b""
            for b, cu in blocks:
                if b[:2] != b"CK":
                    raise CabError("плохой блок MSZIP")
                do = zlib.decompressobj(-15, zdict=prev[-32768:]) if prev else zlib.decompressobj(-15)
                chunk = do.decompress(b[2:])
                out.append(chunk)
                prev = chunk
            stores.append(b"".join(out))
        elif kind == 3:
            stores.append(pzp_lzx.decompress(blocks, (comp >> 8) & 31))
        else:
            raise CabError(f"сжатие cab {kind} не поддерживается")
    res = []
    for name, size, off, fol in files:
        res.append((name, stores[fol][off:off + size]))
    return res
