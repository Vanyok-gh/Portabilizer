#!/usr/bin/env python3
"""
Собирает встроенные наборы библиотек для Portabilizer (папка dx).

Берёт готовые DLL, которые уже стоят в Windows на этом компьютере (после установки
Visual C++ Redistributable, OpenAL и т.п.), и упаковывает их в cab-файлы вида
vc140_x64.cab, vc140_x86.cab, openal_x86.cab. Portabilizer читает такие cab сам
(без сжатия и MSZIP), поэтому ничего больше не нужно: build.bat и GitHub Actions
уже кладут всю папку dx в exe.

Запуск (Windows):   python tools\\collect_redist.py
Куда класть cab:     --out dx   (по умолчанию папка dx рядом с portabilizer_v8.py)
Проверка без записи: --dry-run

Установите перед запуском СВЕЖИЕ пакеты Visual C++ 2015-2022 (x86 и x64): игре,
собранной новым компилятором, нужен такой же или более новый vcruntime140.dll.
"""
import argparse
import os
import struct
import sys
import zlib
from pathlib import Path

PACKS = (
    ("vc140", "Visual C++ 2015-2022",
     ("vcruntime140", "vcruntime140_1", "msvcp140", "msvcp140_1", "msvcp140_2",
      "msvcp140_atomic_wait", "msvcp140_codecvt_ids", "concrt140", "vcomp140")),
    ("vc120", "Visual C++ 2013", ("msvcr120", "msvcp120", "vcomp120")),
    ("vc110", "Visual C++ 2012", ("msvcr110", "msvcp110", "vcomp110")),
    ("vc100", "Visual C++ 2010", ("msvcr100", "msvcp100", "vcomp100")),
    ("openal", "OpenAL", ("openal32",)),
)
MACHINE = {"x86": 0x014C, "x64": 0x8664}


def pe_machine(data: bytes):
    """Тип процессора из заголовка PE или None, если это не PE."""
    if data[:2] != b"MZ" or len(data) < 0x40:
        return None
    pe = struct.unpack("<I", data[0x3C:0x40])[0]
    if data[pe:pe + 4] != b"PE\0\0":
        return None
    return struct.unpack("<H", data[pe + 4:pe + 6])[0]


def file_version(path: Path) -> str:
    """Версия файла (только на Windows), иначе пустая строка."""
    if os.name != "nt":
        return ""
    try:
        import ctypes
        from ctypes import wintypes
        ver = ctypes.windll.version
        size = ver.GetFileVersionInfoSizeW(str(path), None)
        if not size:
            return ""
        buf = ctypes.create_string_buffer(size)
        ver.GetFileVersionInfoW(str(path), 0, size, buf)
        ptr, ln = ctypes.c_void_p(), wintypes.UINT()
        if not ver.VerQueryValueW(buf, "\\", ctypes.byref(ptr), ctypes.byref(ln)):
            return ""
        info = ctypes.string_at(ptr.value, ln.value)
        ms, ls = struct.unpack("<II", info[8:16])
        return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
    except Exception:
        return ""


def cab_write(files: dict) -> bytes:
    """cab с одной папкой и сжатием MSZIP из {имя: байты}. Такой cab читают expand.exe и
    cab_read из Portabilizer."""
    names = sorted(files)
    stream = b"".join(files[n] for n in names)
    blocks, prev = [], b""
    for i in range(0, len(stream), 32768):
        chunk = stream[i:i + 32768]
        co = (zlib.compressobj(9, zlib.DEFLATED, -15, zdict=prev[-32768:]) if prev
              else zlib.compressobj(9, zlib.DEFLATED, -15))
        comp = b"CK" + co.compress(chunk) + co.flush()
        blocks.append(struct.pack("<IHH", 0, len(comp), len(chunk)) + comp)
        prev = chunk
    date = ((2026 - 1980) << 9) | (10 << 5) | 31
    entries, off = [], 0
    for n in names:
        entries.append(struct.pack("<IIHHHH", len(files[n]), off, 0, date, 0, 0x20)
                       + n.encode("ascii") + b"\0")
        off += len(files[n])
    file_table = b"".join(entries)
    coff_files = 36 + 8
    coff_data = coff_files + len(file_table)
    data = b"".join(blocks)
    total = coff_data + len(data)
    header = (b"MSCF" + struct.pack("<IIIII", 0, total, 0, coff_files, 0)
              + struct.pack("<BBHHHHH", 3, 1, 1, len(names), 0, 0x4B31, 0))
    folder = struct.pack("<IHH", coff_data, len(blocks), 1)
    return header + folder + file_table + data


def system_dirs(root: str, x86_dir=None, x64_dir=None) -> dict:
    """Где лежат 32- и 64-разрядные системные DLL. 32-разрядный Python на 64-разрядной
    Windows видит System32 подменённым, настоящий 64-разрядный каталог тогда Sysnative."""
    r = Path(root)
    d64 = Path(x64_dir) if x64_dir else (r / "Sysnative" if (r / "Sysnative").is_dir() else r / "System32")
    d32 = Path(x86_dir) if x86_dir else (r / "SysWOW64" if (r / "SysWOW64").is_dir() else r / "System32")
    return {"x64": d64, "x86": d32}


def collect(dirs: dict, out: Path, dry_run=False, log=print) -> int:
    made = 0
    for pack, title, names in PACKS:
        for arch in ("x86", "x64"):
            got, miss = {}, []
            for n in names:
                p = dirs[arch] / (n + ".dll")
                if not p.is_file():
                    miss.append(n)
                    continue
                data = p.read_bytes()
                if pe_machine(data) != MACHINE[arch]:
                    log(f"  пропускаю {p}: не {arch}")
                    miss.append(n)
                    continue
                got[p.name.lower()] = data
                v = file_version(p)
                log(f"  {title} {arch}: {p.name} {len(data) // 1024} КБ {v}".rstrip())
            if not got:
                log(f"  {title} {arch}: ничего не найдено, набор не создаю")
                continue
            blob = cab_write(got)
            target = out / f"{pack}_{arch}.cab"
            log(f"=> {target.name}: {len(got)} файл(ов), {len(blob) / 1024:.0f} КБ"
                + (f" (нет: {', '.join(miss)})" if miss else ""))
            if not dry_run:
                out.mkdir(parents=True, exist_ok=True)
                target.write_bytes(blob)
            made += 1
    return made


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "dx"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--x86-dir")
    ap.add_argument("--x64-dir")
    a = ap.parse_args(argv)
    root = os.environ.get("SystemRoot", "")
    if not root and not (a.x86_dir and a.x64_dir):
        print("Не найдена папка Windows. Запустите на Windows или укажите --x86-dir и --x64-dir.")
        return 1
    n = collect(system_dirs(root, a.x86_dir, a.x64_dir), Path(a.out), a.dry_run)
    print(f"\nГотово: наборов {n}." + (" Файлы не записаны (--dry-run)." if a.dry_run else
                                      f" Они лежат в {a.out}. Теперь запустите build.bat."))
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
