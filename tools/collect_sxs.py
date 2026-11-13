#!/usr/bin/env python3
"""
Собирает наборы Visual C++ 2005/2008 (side-by-side) для папки dx из установщиков vcredist.

Берёт vcredist_x86.exe / vcredist_x64.exe (2005, 2008), vcredist.msi, merge-модули .msm, cab и zip
(в том числе Data\\vcredist.zip с диска Relic), сам достаёт из них msvcr80/msvcp80/msvcm80, msvcr90/msvcp90/
msvcm90, vcomp и манифесты и пишет cab вида
    sxs_Microsoft.VC80.CRT_8.0.50727.762_x86.cab
Portabilizer (pzp_sxs.py) читает манифест игры и кладёт рядом с ней подходящую версию.
Работает в любой системе, внешние программы не нужны.

Запуск:  python tools/collect_sxs.py vcredist_x86.exe vcredist_x64.exe ...   [--out dx]
"""
import argparse
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import pzp_cab  # noqa: E402
import pzp_msi  # noqa: E402
from collect_redist import cab_write  # noqa: E402

OLE = b"\xD0\xCF\x11\xE0"
DLL_RE = re.compile(r"(?i)^(?P<dll>(?:msvc[rpm]\d0|vcomp\d*)\.dll)\.(?P<rest>.+)$")
MAN_RE = re.compile(r"(?i)^manifest\.(?P<rest>.+)$")


def walk(blob: bytes, out: list, depth=0, log=print):
    """Складывает в out все (имя, байты) из вложенных cab/msi/msm/zip."""
    if depth > 4:
        return
    if blob[:4] == b"MSCF":
        try:
            members = pzp_cab.parse(blob)
        except Exception as e:  # noqa
            log(f"  cab не прочитан: {e}")
            return
        for n, b in members:
            out.append((n, b))
            if b[:4] in (b"MSCF", OLE) and len(b) > 1000:
                walk(b, out, depth + 1, log)
    elif blob[:4] == OLE:
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x.msi"
            p.write_bytes(blob)
            try:
                m = pzp_msi.MSI(str(p))
                for k in list(m.streams):
                    b = m.get(k)
                    if b[:4] in (b"MSCF", OLE):
                        walk(b, out, depth + 1, log)
            except Exception as e:  # noqa
                log(f"  msi не прочитан: {e}")
    elif blob[:2] == b"PK":
        import io
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            for n in z.namelist():
                walk(z.read(n), out, depth + 1, log)
    elif blob[:2] == b"MZ":                       # exe-пакет: внутри лежат cab
        for m in re.finditer(b"MSCF\x00\x00\x00\x00", blob):
            try:
                members = pzp_cab.parse(blob, m.start())
            except Exception:  # noqa
                continue                          # часть вхождений - просто текст внутри кода
            for n, b in members:
                out.append((n, b))
                if b[:4] in (b"MSCF", OLE) and len(b) > 1000:
                    walk(b, out, depth + 1, log)


def identity(manifest: bytes):
    txt = manifest.decode("utf-8-sig", "replace")
    m = re.search(r"<assemblyIdentity\b([^>]*)>", txt, re.S)
    if not m:
        return None
    at = dict(re.findall(r'([\w:]+)\s*=\s*"([^"]*)"', m.group(1)))
    name = at.get("name", "")
    if not re.match(r"(?i)^Microsoft\.VC(80|90)\.(CRT|OpenMP)$", name):
        return None
    arch = at.get("processorArchitecture", "x86").lower()
    return name, at.get("version", ""), "amd64" if arch in ("amd64", "x64") else "x86"


def build(leaves: list):
    """-> {(имя сборки, версия, арх): {файл: байты}}"""
    dlls, mans = {}, {}
    for n, b in leaves:
        m = DLL_RE.match(n)
        if m and b[:2] == b"MZ":
            dlls.setdefault(m.group("rest"), {})[m.group("dll").lower()] = b
            continue
        m = MAN_RE.match(n)
        if m:
            mans[m.group("rest")] = b
    sets = {}
    for rest, man in mans.items():
        ident = identity(man)
        if not ident or rest not in dlls:
            continue
        files = dict(dlls[rest])
        files[ident[0] + ".manifest"] = man
        sets[ident] = files
    return sets


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--out", default=str(HERE.parent / "dx"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    leaves = []
    for s in a.sources:
        print("Читаю", s)
        walk(Path(s).read_bytes(), leaves)
    sets = build(leaves)
    out = Path(a.out)
    for (name, ver, arch), files in sorted(sets.items()):
        target = out / f"sxs_{name}_{ver}_{arch}.cab"
        blob = cab_write(files)
        print(f"=> {target.name}: {', '.join(sorted(files))} ({len(blob) // 1024} КБ)")
        if not a.dry_run:
            out.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
    print(f"\nГотово: наборов {len(sets)}." + (" Файлы не записаны (--dry-run)." if a.dry_run else ""))
    return 0 if sets else 1


if __name__ == "__main__":
    sys.exit(main())
