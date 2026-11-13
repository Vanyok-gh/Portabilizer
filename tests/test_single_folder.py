"""Одиночная папка с msi идёт как один диск; msi без меток тома узнаётся по Setup.exe рядом.
Запуск: python tests/test_single_folder.py"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pzp_disc
import portabilizer_v8 as P

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    coh = t / "COH"; coh.mkdir()
    (coh / "Company of Heroes.msi").write_bytes(b"x")      # не настоящий msi: меток нет
    check(not pzp_disc.is_disc_msi(coh / "Company of Heroes.msi"), "без соседей и меток это не диск")
    (coh / "Setup.exe").write_bytes(b"x")
    check(pzp_disc.is_disc_msi(coh / "Company of Heroes.msi"), "msi рядом с Setup.exe это диск")

    # большой exe-установщик рядом с msi не должен перебивать дисковый msi
    (coh / "DarkCrusadeDemo.exe").write_bytes(b"Nullsoft" + b"\0" * (600 * 1024))
    check(P.find_installer(t).suffix.lower() == ".exe", "обычный поиск берёт большой exe (причина бага)")
    check(P.find_disc_msi(t) == coh / "Company of Heroes.msi", "поиск дискового msi берёт msi")
    (t / "e").mkdir()
    check(P.find_disc_msi(t / "e") is None, "в пустой папке дискового msi нет")

    # пустая папка без установщика: понятное сообщение, не «Файл не найден»
    empty = t / "app"; empty.mkdir(); (empty / "a.txt").write_text("1")
    for i, src in enumerate((str(empty), [str(empty)])):
        logs = []
        ok = P.portabilize(src, str(t / f"out{i}"), logs.append, "auto", "")
        check(ok is False, "папка без установщика не собирается")
        check(any("нет установщика" in x for x in logs), f"сказано про установщик: {logs}")
        check(not any("Файл не найден" in x for x in logs), "нет ложного «Файл не найден»")
print(f"OK: {n} проверок")
