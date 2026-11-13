"""Приложения Visual C++ 2005/2008 (side-by-side): какая именно версия CRT нужна exe и как положить её рядом.

Игры, собранные Visual C++ 2005 и 2008, в манифесте просят точную версию, например
Microsoft.VC80.CRT 8.0.50727.762. Windows ищет её в WinSxS (её ставит vcredist, нужны права
администратора), а если там нет, то рядом с exe: файл Microsoft.VC80.CRT.manifest и сами dll.
Здесь: читаем манифест exe, проверяем WinSxS, берём подходящий набор из папки dx
(sxs_<сборка>_<версия>_<архитектура>.cab) и раскладываем рядом с игрой. Права администратора не нужны."""
import os
import re
from pathlib import Path

import pzp_cab

WANTED = re.compile(r"(?i)^Microsoft\.VC(80|90)\.(CRT|OpenMP)$")
ID_RE = re.compile(r"<assemblyIdentity\b([^>]*)>", re.I | re.S)
ATTR_RE = re.compile(r'([\w:]+)\s*=\s*"([^"]*)"')
SET_RE = re.compile(r"(?i)^sxs_(Microsoft\.VC\d\d\.\w+)_([\d.]+)_(x86|amd64)\.cab$")
MAX_EXE = 400 * 1024 * 1024


def exe_manifest(path) -> str:
    """Текст встроенного манифеста exe (или внешнего <exe>.manifest); пустая строка, если нет."""
    path = Path(path)
    ext = Path(str(path) + ".manifest")
    try:
        if ext.is_file():
            return ext.read_text(encoding="utf-8-sig", errors="replace")
        if path.stat().st_size > MAX_EXE:
            return ""
        data = path.read_bytes()
    except OSError:
        return ""
    best = ""
    start = 0
    while True:
        i = data.find(b"<assembly", start)
        if i < 0:
            break
        j = data.find(b"</assembly>", i)
        if j < 0:
            break
        txt = data[i:j + 11].decode("utf-8", "replace")
        if "dependentAssembly" in txt or "assemblyIdentity" in txt:
            if "dependentAssembly" in txt:
                return txt
            best = best or txt
        start = j + 11
    return best


def needed(manifest: str) -> list:
    """[(сборка, версия, архитектура)] нужных CRT/OpenMP 2005 и 2008 из манифеста.
    Архитектура: x86 или amd64."""
    res = []
    for m in re.finditer(r"<dependentAssembly>(.*?)</dependentAssembly>", manifest, re.S | re.I):
        for a in ID_RE.findall(m.group(1)):
            at = dict(ATTR_RE.findall(a))
            name = at.get("name", "")
            if WANTED.match(name) and at.get("version"):
                arch = at.get("processorArchitecture", "x86").lower()
                res.append((name, at["version"], "amd64" if arch in ("amd64", "x64") else "x86"))
    return res


def sets_index(dx_dir) -> dict:
    """{(сборка, версия, арх): Path к cab} по именам файлов в папке dx."""
    idx = {}
    try:
        for f in Path(dx_dir).iterdir():
            m = SET_RE.match(f.name)
            if m:
                idx[(m.group(1), m.group(2), m.group(3))] = f
    except OSError:
        pass
    return idx


def installed_in_winsxs(name, version, arch, root=None) -> bool:
    """Стоит ли такая сборка в системе (папка WinSxS вида x86_microsoft.vc80.crt_<токен>_<версия>_none_<хэш>)."""
    root = root or os.environ.get("SystemRoot") or ""
    if not root:
        return False
    sx = Path(root) / "WinSxS"
    prefix = f"{arch}_{name}_".lower()
    try:
        for d in sx.iterdir():
            low = d.name.lower()
            if low.startswith(prefix) and f"_{version}_" in low:
                return True
    except OSError:
        pass
    return False


def plan(exe, dx_dir, winsxs_root=None) -> dict:
    """Что нужно exe: {'need': [...], 'have': [...] (уже в системе или рядом), 'place': [(ключ, cab)],
    'missing': [ключ] (в dx нет такой версии)}."""
    exe = Path(exe)
    idx = sets_index(dx_dir)
    res = {"need": needed(exe_manifest(exe)), "have": [], "place": [], "missing": []}
    for key in res["need"]:
        name, ver, arch = key
        if (exe.parent / f"{name}.manifest").is_file() or (exe.parent / name / f"{name}.manifest").is_file():
            res["have"].append(key)
        elif installed_in_winsxs(name, ver, arch, winsxs_root):
            res["have"].append(key)
        elif key in idx:
            res["place"].append((key, idx[key]))
        else:
            res["missing"].append(key)
    return res


def place(exe, plan_, log) -> int:
    """Раскладывает наборы рядом с exe. Возвращает число разложенных сборок."""
    n = 0
    for (name, ver, arch), cab in plan_["place"]:
        try:
            files = pzp_cab.parse(Path(cab).read_bytes())
        except (OSError, pzp_cab.CabError) as e:
            log(f"Visual C++ {name} {ver}: набор не читается ({e})")
            continue
        for fname, data in files:
            (Path(exe).parent / fname).write_bytes(data)
        log(f"Visual C++: {name} {ver} ({arch}) положен рядом с игрой, права администратора не нужны.")
        n += 1
    return n
