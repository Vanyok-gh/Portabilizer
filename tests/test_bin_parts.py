"""Проверка частей установщика Inno (<имя>-N.bin)."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P  # noqa: E402

fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


def mk(files):
    d = Path(tempfile.mkdtemp())
    for n, sz in files.items():
        (d / n).write_bytes(b"x" * sz)
    return d / "setup_game.exe", sorted(d.glob("*.bin"))


exe, bins = mk({"setup_game-1.bin": 100, "setup_game-2.bin": 100, "setup_game-3.bin": 40})
check(P.check_bin_parts(exe, bins) == [], "полный набор: замечаний нет")

exe, bins = mk({"setup_game-1.bin": 100, "setup_game-3.bin": 100})
r = P.check_bin_parts(exe, bins)
check(len(r) == 1 and "setup_game-2.bin" in r[0], "пропущена часть 2 - названа в сообщении")

exe, bins = mk({"setup_game-1.bin": 100, "setup_game-2.bin": 60, "setup_game-3.bin": 100, "setup_game-4.bin": 10})
r = P.check_bin_parts(exe, bins)
check(any("setup_game-2.bin" in x and "не докачаны" in x for x in r), "обрезанная часть 2 найдена")

exe, bins = mk({"setup_game-1.bin": 0, "setup_game-2.bin": 100})
check(any("Пустые" in x for x in P.check_bin_parts(exe, bins)), "пустая часть найдена")

exe, bins = mk({"data.bin": 100})
check(P.check_bin_parts(exe, bins) == [], "чужой .bin не считается частями")

print("\nпровалов:", len(fails))
sys.exit(1 if fails else 0)
