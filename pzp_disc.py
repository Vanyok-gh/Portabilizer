"""Оцифровка дисковых игр (v10): всё, что можно узнать из установщика и сделать без прав администратора.

Что умеет:
- msi_registry / reg_text: таблица Registry установщика -> .reg для HKCU (HKLM переводим в HKCU, путь установки {ROOT}).
- disc_labels: метки томов дисков из таблицы Media (TRAOD1, TRAOD2 ...).
- disc_layout_dirs / merge_disc_layout: каталоги «с диска» (рядом с каталогом установки) переносим в каталог игры.
- apply_patches: проверенные патчи совместимости exe (сигнатура, ровно одно совпадение, копия .bak).
Только чтение msi; любые ошибки разбора вызывающий код считает «не знаю» и продолжает работу.
Никаких обходов защиты от копирования здесь нет: патчи только про совместимость с современной Windows.
"""
import re
import shutil
from pathlib import Path

from pzp_msi import MSI, _src_name

# Каталоги первого уровня, которые не относятся к игре (системные компоненты на диске)
DISC_SKIP = ("directx9", "directx", "eaxunified", "redist", "dotnet", "vcredist", "isscript")

ROOT_NAMES = {-1: "HKEY_CURRENT_USER", 0: "HKEY_CURRENT_USER\\Software\\Classes", 1: "HKEY_CURRENT_USER",
              2: "HKEY_CURRENT_USER"}     # HKLM -> HKCU: администратор не нужен


def _tables(msi_path):
    m = MSI(msi_path)
    return m


def _props(m) -> dict:
    try:
        return {r[0]: str(r[1]) for r in m.table("Property")[1]}
    except Exception:
        return {}


def _dirs(m) -> dict:
    return {r[0]: (r[1], r[2]) for r in m.table("Directory")[1]}


def install_rel(msi_path) -> list:
    """Путь INSTALLDIR внутри административного образа (как его раскладывает msiexec /a): список имён папок."""
    m = _tables(msi_path)
    d = _dirs(m)
    parts, k, guard = [], "INSTALLDIR", 0
    while k in d and k != "TARGETDIR" and guard < 40:
        guard += 1
        parent, default = d[k]
        name = _src_name(default)
        if name not in (".", ""):
            parts.append(name)
        k = parent
    return parts[::-1]


def disc_labels(msi_path) -> list:
    """Метки томов в порядке дисков, без повторов: ['TRAOD1', 'TRAOD2']."""
    m = _tables(msi_path)
    out = []
    try:
        for r in sorted(m.table("Media")[1], key=lambda r: r[0]):
            v = str(r[4]).strip()
            if v and v not in out:
                out.append(v)
    except Exception:
        pass
    return out


def _subst(value: str, props: dict) -> str:
    def rep(mo):
        k = mo.group(1)
        if k == "INSTALLDIR":
            return "{INSTALLDIR}"
        return props.get(k, mo.group(0))
    return re.sub(r"\[([A-Za-z_][A-Za-z0-9_]*)\]", rep, value)


def msi_registry(msi_path) -> list:
    """Записи реестра установщика: [{'root','key','name','value','kind'}], kind: sz / dword / expand / hex / key."""
    m = _tables(msi_path)
    props = _props(m)
    out = []
    try:
        rows = m.table("Registry")[1]
    except Exception:
        return out
    for r in rows:
        root, key, name, value = r[1], str(r[2]), str(r[3] or ""), r[4]
        value = "" if value is None else str(value)
        if root not in ROOT_NAMES or not key or name in ("-", "*"):
            continue
        if name == "+":
            name = ""
        key = _subst(key, props)
        if name == "" and value == "":
            out.append({"root": root, "key": key, "name": "", "value": "", "kind": "key"})
            continue
        kind = "sz"
        if value.startswith("##"):
            value = value[1:]
        elif value.startswith("#%"):
            kind, value = "expand", value[2:]
        elif value.startswith("#x"):
            kind, value = "hex", value[2:]
        elif value.startswith("#"):
            v = _subst(value[1:], props)
            if re.fullmatch(r"-?\d+", v):
                kind, value = "dword", v
            else:
                continue
        if kind in ("sz", "expand"):
            value = _subst(value, props)
        if value.startswith("[~]") or "[~]" in value:
            continue
        out.append({"root": root, "key": key, "name": name, "value": value, "kind": kind})
    return out


def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def reg_text(entries: list, install_path: str) -> str:
    """Текст .reg. install_path - путь каталога установки, например '{ROOT}\\App\\program files\\X\\TRAOD'.
    В файле остаётся {ROOT}: Portable.ps1 подставит актуальную папку при запуске."""
    ip = install_path.rstrip("\\") + "\\"
    lines = ["Windows Registry Editor Version 5.00", ""]
    cur = None
    for e in entries:
        head = ROOT_NAMES[e["root"]] + "\\" + e["key"]
        if head != cur:
            lines += ["", "[" + head + "]"]
            cur = head
        if e["kind"] == "key":
            continue
        nm = "@" if e["name"] == "" else _q(e["name"])
        val = e["value"].replace("{INSTALLDIR}", ip)
        if e["kind"] == "dword":
            lines.append(f"{nm}=dword:{int(val) & 0xFFFFFFFF:08x}")
        elif e["kind"] == "expand":
            raw = val.encode("utf-16le") + b"\0\0"
            lines.append(f"{nm}=hex(2):" + ",".join(f"{b:02x}" for b in raw))
        elif e["kind"] == "hex":
            raw = bytes.fromhex(val) if re.fullmatch(r"([0-9a-fA-F]{2})*", val) else b""
            lines.append(f"{nm}=hex:" + ",".join(f"{b:02x}" for b in raw))
        else:
            lines.append(f"{nm}={_q(val)}")
    return "\r\n".join(lines) + "\r\n"


def disc_layout_dirs(msi_path) -> list:
    """Имена папок первого уровня образа, которые лежат рядом с каталогом установки (файлы «с диска»)."""
    m = _tables(msi_path)
    d = _dirs(m)
    anc, k = set(), "INSTALLDIR"
    while k in d:
        anc.add(k)
        k = d[k][0]
    names = []
    for key, (parent, default) in d.items():
        if parent != "TARGETDIR" or key in anc or ":" in default:     # '.:...' - системные папки Windows
            continue
        n = _src_name(default)
        if n and n.lower() not in DISC_SKIP and n not in names:
            names.append(n)
    return names


def _ci_child(folder: Path, name: str):
    try:
        for p in folder.iterdir():
            if p.is_dir() and p.name.lower() == name.lower():
                return p
    except OSError:
        pass
    return None


def merge_disc_layout(extract_root: Path, install_dir: Path, names: list, log) -> int:
    """Переносит (не копирует: место не тратится) каталоги «с диска» в каталог игры, без перезаписи.
    Папка Data рядом с каталогом установки -> <игра>\\data (имена сравниваются без учёта регистра)."""
    moved = 0
    for name in names:
        src = _ci_child(extract_root, name)
        dst = _ci_child(install_dir, name)
        if not src or not dst or src == dst:
            continue
        n = _merge_dir(src, dst)
        if n:
            log(f"Файлы с диска: {n} шт. перенесено из {src.name} в {dst.relative_to(install_dir.parent) if install_dir.parent in dst.parents else dst}")
        moved += n
        try:
            src.rmdir()           # удалится только если пуст
        except OSError:
            pass
    return moved


def _merge_dir(src: Path, dst: Path) -> int:
    n = 0
    for p in list(src.iterdir()):
        t = dst / p.name
        if p.is_dir():
            sub = _ci_child(dst, p.name)
            if sub is None:
                sub = dst / p.name
                sub.mkdir(parents=True, exist_ok=True)
            n += _merge_dir(p, sub)
            try:
                p.rmdir()
            except OSError:
                pass
        else:
            ex = next((q for q in dst.iterdir() if q.name.lower() == p.name.lower()), None) if dst.exists() else None
            if ex is None:
                dst.mkdir(parents=True, exist_ok=True)
                shutil.move(str(p), str(t))
                n += 1
    return n


# ---------------------------------------------------------------------------------------------
# Патчи совместимости. Каждый: сигнатура (hex), смещение изменяемого байта внутри неё, старое/новое значение.
# Применяем только если сигнатура найдена РОВНО один раз; оригинал сохраняется как <файл>.bak.
PATCHES = [
    {
        "id": "core-vmr9-default",
        "title": "Core Design engine: use VMR9 video by default (old overlay mixer fails on Windows 10/11)",
        "sig": bytes.fromhex("8a90fb160000" "84d2" "7508" "b801000000" "595ec3"),
        "at": 8, "old": 0x75, "new": 0xEB,
    },
]


def find_all(data: bytes, pat: bytes) -> list:
    out, i = [], data.find(pat)
    while i >= 0:
        out.append(i)
        i = data.find(pat, i + 1)
    return out


def _candidates(install_dir: Path):
    seen = set()
    for folder in (install_dir / "bin", install_dir):
        if folder.is_dir():
            for p in sorted(folder.glob("*.exe")):
                if p not in seen:
                    seen.add(p)
                    yield p


def apply_patches(install_dir: Path, log, patches=None, undo=False) -> list:
    """[(файл, id, статус)], статус: patched / already / restored. Не найденные патчи молча пропускаются."""
    res = []
    for exe in _candidates(install_dir):
        bak = exe.with_name(exe.name + ".bak")
        if undo:
            if bak.exists():
                shutil.copy2(bak, exe)
                res.append((exe, "*", "restored"))
            continue
        try:
            if exe.stat().st_size > 128 * 1024 * 1024:
                continue
            data = bytearray(exe.read_bytes())
        except OSError:
            continue
        changed = False
        for p in (patches or PATCHES):
            sig = p["sig"]
            hits = find_all(bytes(data), sig)
            if len(hits) == 1:
                i = hits[0] + p["at"]
                if data[i] == p["old"]:
                    data[i] = p["new"]
                    changed = True
                    res.append((exe, p["id"], "patched"))
                continue
            done = bytearray(sig)
            done[p["at"]] = p["new"]
            if len(find_all(bytes(data), bytes(done))) == 1:
                res.append((exe, p["id"], "already"))
        if changed:
            try:
                if not bak.exists():
                    bak.write_bytes(exe.read_bytes())
                exe.write_bytes(bytes(data))
            except OSError as e:
                log(f"Патч {exe.name}: не удалось записать ({e})")
                res = [r for r in res if r[0] != exe]
    for exe, pid, st in res:
        log(f"Патч совместимости «{pid}»: {exe.name} - {st}")
    return res


def analyze(msi_path) -> dict:
    """Всё, что известно об установщике для оцифровки игры (ошибки разбора -> пустые значения)."""
    out = {"labels": [], "registry": [], "layout": [], "install_rel": []}
    for key, fn in (("labels", disc_labels), ("registry", msi_registry), ("layout", disc_layout_dirs),
                    ("install_rel", install_rel)):
        try:
            out[key] = fn(msi_path)
        except Exception:
            pass
    return out


# ---------------------------------------------------------------------------------------------
# Подсказки по готовой папке игры (когда установщика нет): что видно в самом exe. Exe не запускается.
_REG_RE = re.compile(rb"(?i)software\\[\w .\-\\]{3,}")
_REG_SKIP = ("microsoft", "classes", "policies", "wow6432node\\microsoft")


def scan_exe_hints(exe, limit=64 * 1024 * 1024) -> dict:
    """{'registry': [ключи HKLM/HKCU, которые exe читает], 'disc_check': bool, 'disc_prompts': [строки]}.
    Значения ключей по exe узнать нельзя, только их пути: это подсказка, что именно игра ищет в реестре."""
    res = {"registry": [], "disc_check": False, "disc_prompts": []}
    try:
        with open(exe, "rb") as f:
            data = f.read(limit)
    except OSError:
        return res
    strs = re.findall(rb"[\x20-\x7e]{6,}", data)                                           # ASCII-строки
    strs += [m.replace(b"\x00", b"") for m in re.findall(rb"(?:[\x20-\x7e]\x00){6,}", data)]  # UTF-16
    seen = set()
    for m in (g for st in strs for g in _REG_RE.findall(st)):
        k = m.decode("latin1").rstrip("\\")
        low = k.lower().replace("software\\", "", 1)
        if k.lower() in seen or any(low.startswith(s) for s in _REG_SKIP) or k.count("\\") < 1:
            continue
        seen.add(k.lower())
        res["registry"].append(k)
    res["disc_check"] = b"GetVolumeInformation" in data and b"GetDriveType" in data
    prompts = re.findall(rb"(?i)[\x20-\x7e]{0,60}(?:insert (?:the )?(?:correct |game |cd|dvd|disc|disk)|please insert)[\x20-\x7e]{0,60}", data)
    res["disc_prompts"] = sorted({p.decode("latin1").strip() for p in prompts})[:5]
    return res


# ---------------------------------------------------------------------------------------------
# Несколько дисков в одном задании: .cab второго диска должны лежать рядом с msi первого.
def cabinets(msi_path) -> list:
    """[(имя .cab, метка диска)] для внешних кабинетов (без '#' = внутри msi)."""
    m = _tables(msi_path)
    out = []
    try:
        for r in m.table("Media")[1]:
            cab = str(r[3] or "").strip()
            if cab and not cab.startswith("#"):
                out.append((cab, str(r[4] or "").strip()))
    except Exception:
        pass
    return out


def _find_file(root: Path, name: str, depth: int = 3):
    import os
    root = str(root)
    base = root.rstrip("\\/").count(os.sep)
    low = name.lower()
    for cur, dirs, files in os.walk(root):
        if cur.rstrip("\\/").count(os.sep) - base >= depth:
            dirs[:] = []
        for f in files:
            if f.lower() == low:
                return Path(cur) / f
    return None


def _place(src: Path, dst: Path):
    """Жёсткая ссылка (место не тратится, права не нужны), иначе копия."""
    import os
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def gather_cabinets(msi_path, search_root, log, placed=None) -> list:
    """Ищет недостающие .cab (по таблице Media) в search_root и кладёт их рядом с msi.
    Возвращает список так и не найденных: [(cab, метка диска)]."""
    msi_path = Path(msi_path)
    missing = []
    for cab, label in cabinets(msi_path):
        here = msi_path.parent / cab
        if here.exists():
            continue
        found = _find_file(Path(search_root), cab) if search_root else None
        if found and found.resolve() != here.resolve():
            try:
                _place(found, here)
                if placed is not None:
                    placed.append(here)
                log(f"Кабинет {cab} (диск {label or '?'}) найден в {found.parent} и подключён к установщику.")
                continue
            except OSError as e:
                log(f"Не удалось подключить {cab}: {e}")
        missing.append((cab, label))
    for cab, label in missing:
        log(f"Не найден {cab} рядом с msi (он на диске {label or '?'}). Положите его рядом с установщиком "
            f"или в соседнюю папку диска {label or ''}.")
    return missing
