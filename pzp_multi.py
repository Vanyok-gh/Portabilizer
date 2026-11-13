"""Несколько дисков в одном задании (v10.3): папки, архивы и образы раскладываются в одну рабочую
папку с английскими именами Disc1, Disc2..., дальше сборка идёт как обычно.
Модуль без интерфейса и без зависимостей от основной программы: распаковка передаётся функцией."""
import os
import re
import shutil
from pathlib import Path

ARCHIVE_EXT = (".zip", ".7z", ".rar", ".iso", ".tar", ".gz", ".tgz", ".xz", ".bz2", ".cab")


def disc_dir_name(i: int) -> str:
    return f"Disc{i}"


def _link_or_copy(src: Path, dst: Path):
    """Жёсткая ссылка (место не тратится), иначе копия."""
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def link_tree(src: Path, dst: Path, should_stop=None) -> int:
    """Копирует дерево папок: файлы жёсткими ссылками, где можно. Возвращает число файлов."""
    n = 0
    dst.mkdir(parents=True, exist_ok=True)
    for cur, dirs, files in os.walk(src):
        if should_stop and should_stop():
            raise InterruptedError()
        rel = Path(cur).relative_to(src)
        (dst / rel).mkdir(parents=True, exist_ok=True)
        for f in files:
            _link_or_copy(Path(cur) / f, dst / rel / f)
            n += 1
    return n


def disc_root(folder: Path) -> Path:
    """Настоящий корень диска: заходим внутрь, пока в папке лежит только одна подпапка
    (архив, который собрали вместе с внешней папкой, и т.п.)."""
    folder = Path(folder)
    for _ in range(4):
        try:
            items = [p for p in folder.iterdir()]
        except OSError:
            break
        if len(items) == 1 and items[0].is_dir():
            folder = items[0]
        else:
            break
    return folder


def stage_sources(sources, staging: Path, log, extract_fn, should_stop=None) -> list:
    """sources: пути к папкам и файлам. extract_fn(файл, папка) -> bool распаковывает архив/образ.
    Возвращает список корней дисков (Disc1, Disc2...) в порядке источников; не вышедшие пропускаются."""
    staging = Path(staging)
    roots = []
    for i, s in enumerate(sources, 1):
        s = Path(s)
        dst = staging / disc_dir_name(i)
        if not s.exists():
            log(f"Источник не найден: {s}")
            continue
        if dst.exists():
            shutil.rmtree(dst, ignore_errors=True)
        dst.mkdir(parents=True, exist_ok=True)
        if s.is_dir():
            log(f"Диск {i}: беру папку {s.name}.")
            try:
                link_tree(s, dst, should_stop)
            except InterruptedError:
                raise
            except OSError as e:
                log(f"Не удалось скопировать {s}: {e}")
                continue
        elif s.suffix.lower() in ARCHIVE_EXT:
            log(f"Диск {i}: распаковываю {s.name}.")
            if not extract_fn(s, dst):
                log(f"Не удалось распаковать {s.name}.")
                continue
        else:
            log(f"Диск {i}: кладу файл {s.name}.")
            try:
                _link_or_copy(s, dst / s.name)
            except OSError as e:
                log(f"Не удалось скопировать {s}: {e}")
                continue
        roots.append(disc_root(dst))
    return roots


def find_file(root: Path, name: str, depth: int = 3):
    base = str(root).rstrip("\\/").count(os.sep)
    low = name.lower()
    for cur, dirs, files in os.walk(root):
        if cur.rstrip("\\/").count(os.sep) - base >= depth:
            dirs[:] = []
        for f in files:
            if f.lower() == low:
                return Path(cur) / f
    return None


def assign_labels(roots, msi: Path, labels: list, cabinets: list) -> dict:
    """{корень диска: метка тома}. Диск с msi получает первую метку (диск 1),
    диск с кабинетом получает метку этого кабинета из таблицы Media."""
    out = {}
    msi = Path(msi)
    for r in roots:
        try:
            msi.relative_to(r)
        except ValueError:
            continue
        if labels:
            out[Path(r)] = labels[0]
        break
    used = set(out.values())
    for cab, label in cabinets:
        if not label or label in used:
            continue
        for r in roots:
            if Path(r) in out:
                continue
            if find_file(Path(r), cab):
                out[Path(r)] = label
                used.add(label)
                break
    return out


def safe_label(name: str) -> str:
    """Метка тома из имени папки, если в msi её нет: латиница, цифры и _ (не более 32)."""
    s = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_")
    return (s or "DISC").upper()[:32]
