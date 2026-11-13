"""Установщик Relic (gameInst.exe + Data\\Install.lua) без запуска самого установщика.

Так ставятся Company of Heroes: Tales of Valor и родственные игры Relic. Данные лежат в Data\\<ID>
или Data\\<ID>.zip, где ID = <имя>.<MD5>.NEW; список файлов и их путей - в Data\\Install.lua(.zip).
Мы разбираем скрипт, раскладываем файлы по путям, проверяем MD5 и пишем настройки реестра в .reg (HKCU).
Любая ошибка разбора - не исключение наружу, а понятный результат; вызывающий код пишет в лог.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

FILE_RE = re.compile(
    r'\{\s*Progress\s*=\s*(\d+)\s*,\s*ID\s*=\s*"([^"]+)"\s*,\s*Md5Sum\s*=\s*"([0-9A-Fa-f]{32})"\s*,'
    r'\s*Path\s*=\s*L"([^"]+)"\s*\}')
DIR_RE = re.compile(r'\{\s*Progress\s*=\s*\d+\s*,\s*Path\s*=\s*L"([^"]+)"\s*\}')
SCALAR_RE = r'^\s*%s\s*=\s*L?"([^"]*)"'
# файлы, которые установщик берёт из Data, но в AddedFiles их нет
EXTRA_PREFIXES = ("readme_",)
CHUNK = 1 << 20


class RelicError(Exception):
    pass


def _ci_child(folder, name):
    """Дочерний элемент папки без учёта регистра (или None)."""
    try:
        low = name.lower()
        for x in os.listdir(folder):
            if x.lower() == low:
                return Path(folder) / x
    except OSError:
        pass
    return None


def find_root(folder, depth=2):
    """Корень диска Relic: папка с gameInst.exe и Data\\Install.lua(.zip). Ищет на глубину depth."""
    folder = Path(folder)
    if not folder.is_dir():
        return None
    if _ci_child(folder, "gameInst.exe"):
        data = _ci_child(folder, "Data")
        if data and data.is_dir() and (_ci_child(data, "Install.lua") or _ci_child(data, "Install.lua.zip")):
            return folder
    if depth > 0:
        try:
            subs = sorted(x for x in folder.iterdir() if x.is_dir())
        except OSError:
            return None
        for s in subs:
            r = find_root(s, depth - 1)
            if r:
                return r
    return None


def read_script(root):
    data = _ci_child(Path(root), "Data")
    if not data:
        raise RelicError("нет папки Data")
    lua = _ci_child(data, "Install.lua")
    if lua:
        raw = lua.read_bytes()
    else:
        z = _ci_child(data, "Install.lua.zip")
        if not z:
            raise RelicError("нет Install.lua")
        with zipfile.ZipFile(z) as zf:
            names = zf.namelist()
            if not names:
                raise RelicError("Install.lua.zip пуст")
            raw = zf.read(names[0])
    for enc in ("utf-8-sig", "utf-16", "cp1251", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeError:
            continue
    return raw.decode("latin-1", "replace")


def _clean_path(p):
    p = p.replace("\\\\", "\\").replace("/", "\\").strip("\\")
    parts = [x for x in p.split("\\") if x]
    if not parts or any(x == ".." or ":" in x for x in parts):
        return None
    return tuple(parts)


def _block(text, name):
    m = re.search(r'^\s*%s\s*=\s*\{' % re.escape(name), text, re.M)
    if not m:
        return ""
    i = m.end()
    depth = 1
    while i < len(text) and depth:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return text[m.end():i]


def parse_script(text):
    """-> dict(files=[(id, md5, relparts)], dirs=[relparts], locale, exe, name, version, key_path)."""
    files, seen = [], set()
    for _prog, fid, md5, path in FILE_RE.findall(_block(text, "AddedFiles")):
        rel = _clean_path(path)
        if rel is None:
            continue
        key = tuple(x.lower() for x in rel)
        if key in seen:
            continue
        seen.add(key)
        files.append((fid, md5.upper(), rel))
    dirs = []
    for path in DIR_RE.findall(_block(text, "AddedDirectories")):
        rel = _clean_path(path)
        if rel:
            dirs.append(rel)

    def scalar(n):
        m = re.search(SCALAR_RE % n, text, re.M)
        return m.group(1) if m else ""
    return {"files": files, "dirs": dirs, "locale": scalar("LocaleID"), "exe": scalar("AppExeName"),
            "name": scalar("AppName"), "version": scalar("NewVersion"),
            "key_path": scalar("CohKeyPath").replace("\\\\", "\\")}


def _data_source(data_dir, fid):
    """Источник для ID: (путь, zipped) без учёта регистра."""
    p = _ci_child(data_dir, fid)
    if p and p.is_file():
        return p, False
    p = _ci_child(data_dir, fid + ".zip")
    if p and p.is_file():
        return p, True
    return None, False


def _move_verified(src, dest, stop=None):
    """Источник одноразовый (распакованный архив): считаем MD5 и переименовываем файл без копии (нет лишнего места)."""
    h = hashlib.md5()
    with open(src, "rb") as f:
        while True:
            if stop and stop():
                raise InterruptedError
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.replace(src, dest)
    except OSError:
        shutil.move(str(src), str(dest))
    return h.hexdigest().upper()


def _copy_verified(src, zipped, dest, want_md5, stop=None):
    """Копирует (или распаковывает) src в dest, считая MD5. Возвращает md5 записанного."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.md5()
    tmp = dest.with_name(dest.name + ".part")
    try:
        if zipped:
            zf = zipfile.ZipFile(src)
            infos = [i for i in zf.infolist() if not i.is_dir()]
            if not infos:
                raise RelicError("пустой zip")
            want = (os.path.basename(str(src))[:-4]).lower()
            info = next((i for i in infos if i.filename.lower().replace("\\", "/").split("/")[-1] == want), infos[0])
            fin = zf.open(info)
        else:
            zf = None
            fin = open(src, "rb")
        with fin, open(tmp, "wb") as out:
            while True:
                if stop and stop():
                    raise InterruptedError
                b = fin.read(CHUNK)
                if not b:
                    break
                h.update(b)
                out.write(b)
        if zf:
            zf.close()
        os.replace(tmp, dest)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
    return h.hexdigest().upper()


def source_size(root, plan):
    data = _ci_child(Path(root), "Data")
    total = 0
    for fid, _m, _rel in plan["files"]:
        p, _z = _data_source(data, fid)
        if p:
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def _is_extra(name):
    n = name.lower()
    return n.startswith(EXTRA_PREFIXES) or n in ("reliccoh_icon.png", "reliccoh.mcl")


def install(root, app, log, stop=None, progress=None, check_space=True, consume=False):
    """Раскладывает игру в app. -> dict(total, done, missing, bad_md5, exe, locale, name, version, key_path).
    stop() -> True: прервать (InterruptedError). progress(done, total): вызывается после каждого файла.
    consume=True: источник - временная распаковка архива; файлы переносятся (а .zip удаляются после распаковки),
    поэтому пик места почти равен размеру самой игры, а не двум."""
    root, app = Path(root), Path(app)
    plan = parse_script(read_script(root))
    if not plan["files"]:
        raise RelicError("в Install.lua нет списка файлов")
    data = _ci_child(root, "Data")
    app.mkdir(parents=True, exist_ok=True)
    if check_space and not consume:
        need = source_size(root, plan)
        try:
            free = shutil.disk_usage(app).free
            if free < need * 1.05:
                raise RelicError(f"Мало места: нужно около {need // 2**20} МБ, свободно {free // 2**20} МБ")
        except OSError:
            pass
    for d in plan["dirs"]:
        (app.joinpath(*d)).mkdir(parents=True, exist_ok=True)
    total = len(plan["files"])
    missing, bad = [], []
    for i, (fid, md5, rel) in enumerate(plan["files"], 1):
        if stop and stop():
            raise InterruptedError
        src, zipped = _data_source(data, fid)
        if src is None:
            missing.append("\\".join(rel))
        else:
            dest = app.joinpath(*rel)
            try:
                if consume and not zipped:
                    got = _move_verified(src, dest, stop)
                else:
                    got = _copy_verified(src, zipped, dest, md5, stop)
                    if consume:
                        try:
                            src.unlink()
                        except OSError:
                            pass
            except (RelicError, zipfile.BadZipFile, OSError) as e:
                log("Relic: " + "\\".join(rel) + f": ошибка ({e})")
                bad.append("\\".join(rel))
            else:
                if got != md5:
                    bad.append("\\".join(rel))
        if progress:
            progress(i, total)
    # файлы вне списка: Readme_*.txt, иконка, .mcl
    extras = 0
    for x in sorted(os.listdir(data)):
        base = x[:-4] if x.lower().endswith(".zip") else x
        if not _is_extra(base) or base.lower().endswith(".new"):
            continue
        src = Path(data) / x
        try:
            if x.lower().endswith(".zip"):
                with zipfile.ZipFile(src) as zf:
                    for info in zf.infolist():
                        nm = info.filename.replace("\\", "/").split("/")[-1]
                        if info.is_dir() or not nm:
                            continue
                        with zf.open(info) as fi, open(app / nm, "wb") as fo:
                            shutil.copyfileobj(fi, fo)
            else:
                shutil.copy2(src, app / x)
            extras += 1
        except (OSError, zipfile.BadZipFile):
            pass
    return {"total": total, "missing": missing, "bad_md5": bad, "extras": extras,
            "exe": plan["exe"], "locale": plan["locale"], "name": plan["name"],
            "version": plan["version"], "key_path": plan["key_path"]}


def registry_text(info):
    """Текст .reg (HKCU) с состоянием установки; {ROOT} подставляет Portable.ps1. -> (text, key)"""
    kp = info.get("key_path") or "HKEY_LOCAL_MACHINE\\SOFTWARE\\THQ\\Company of Heroes"
    kp = re.sub(r"^HKEY_LOCAL_MACHINE", "HKEY_CURRENT_USER", kp, flags=re.I)
    lines = ["Windows Registry Editor Version 5.00", "", f"[{kp}]",
             '"CoHInstallState"="Installed"',
             '"InstallDir"="{ROOT}\\\\App"', ""]
    return "\r\n".join(lines), kp


# --- VC++ 2005 SP1 (8.0.50727.762): рядом с exe, чтобы игра не просила установить среду

CRT_FILES = ("msvcr80.dll", "msvcp80.dll", "msvcm80.dll")


def _crt_cab_from_vcredist(root, workdir):
    """Достаёт CAB с CRT из Data\\vcredist.zip -> vcredist.msi -> поток *VC80_CRT_x86.msm."""
    data = _ci_child(Path(root), "Data")
    z = _ci_child(data, "vcredist.zip") if data else None
    if not z:
        return None
    with zipfile.ZipFile(z) as zf:
        nm = next((n for n in zf.namelist() if n.lower().endswith("vcredist.msi")), None)
        if not nm:
            return None
        msi_path = Path(workdir) / "vcredist.msi"
        msi_path.write_bytes(zf.read(nm))
    import pzp_msi
    m = pzp_msi.MSI(str(msi_path))
    key = next((k for k in m.streams if "vc80_crt_x86" in k.lower()), None)
    if not key:
        return None
    cab = Path(workdir) / "crt.cab"
    cab.write_bytes(m.get(key))
    return cab


def vc80_runtime(root, exe_dir, log, run=None):
    """Кладёт msvcr80/msvcp80/msvcm80 (8.0.50727.762) и манифест рядом с exe. True, если среда на месте.
    run(cmd) -> returncode: подмена для тестов; по умолчанию Windows expand.exe."""
    exe_dir = Path(exe_dir)
    if all((exe_dir / n).is_file() for n in CRT_FILES[:1]) and (exe_dir / "Microsoft.VC80.CRT.manifest").is_file():
        return True
    if run is None and not sys.platform.startswith("win"):
        log("VC++ 2005: не Windows, пропускаю (положите msvcr80.dll рядом с игрой, если её нет).")
        return False
    work = tempfile.mkdtemp(prefix="pzp_vc80_")
    try:
        cab = _crt_cab_from_vcredist(root, work)
        if not cab:
            log("VC++ 2005: в Data нет vcredist.zip с нужной средой - пропускаю.")
            return False
        out = Path(work) / "x"
        out.mkdir()
        cmd = ["expand.exe", str(cab), "-F:*", str(out)]
        if run is not None:
            rc = run(cmd)
        else:
            rc = subprocess.run(cmd, capture_output=True,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode
        if rc not in (0, None):
            log(f"VC++ 2005: expand.exe вернул код {rc}")
            return False
        got = 0
        for f in out.iterdir():
            low = f.name.lower()
            m = re.match(r"(msvc[rpm]80\.dll)\.8\.0\.50727\.762", low)
            if m:
                shutil.copy2(f, exe_dir / m.group(1))
                got += 1
            elif low.startswith("manifest.8.0.50727.762"):
                shutil.copy2(f, exe_dir / "Microsoft.VC80.CRT.manifest")
                got += 1
        if got:
            log(f"VC++ 2005 SP1: положил {got} файл(ов) среды рядом с игрой.")
        else:
            log("VC++ 2005: нужные файлы в архиве среды не найдены.")
        return got > 0
    except Exception as e:
        log(f"VC++ 2005: не удалось подготовить среду ({e})")
        return False
    finally:
        shutil.rmtree(work, ignore_errors=True)
