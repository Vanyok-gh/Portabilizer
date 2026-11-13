"""Несколько дисков в одном задании (pzp_multi + _portabilize_multi). Запуск: python tests/test_multi.py"""
import sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pzp_multi as M

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

def zex(f, d):
    zipfile.ZipFile(f).extractall(d); return True

with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    # диск 1: папка с кириллицей, внутри ещё одна папка (как «Диск 1\TRAOD1»)
    d1 = t / "Диск 1" / "TRAOD1"; (d1 / "Data").mkdir(parents=True)
    (d1 / "Setup.msi").write_bytes(b"x"); (d1 / "Data" / "a.bin").write_bytes(b"1")
    # диск 2: zip, внешняя папка + Release.cab
    z2 = t / "Диск 2.zip"
    with zipfile.ZipFile(z2, "w") as z:
        z.writestr("TRAOD2/Release.cab", b"c"); z.writestr("TRAOD2/Data/b.bin", b"2")
    logs = []
    stg = t / "stg"
    roots = M.stage_sources([t / "Диск 1", z2, t / "нет"], stg, logs.append, zex)
    check(len(roots) == 2, f"два диска подготовлены, пропущен несуществующий: {roots}")
    check(roots[0].name == "TRAOD1" and (roots[0] / "Setup.msi").is_file(), "корень диска 1 найден внутри вложенной папки")
    check(roots[1].name == "TRAOD2" and (roots[1] / "Release.cab").is_file(), "корень диска 2 найден внутри zip")
    check(all(str(r).isascii() for r in roots), "путь рабочей папки латинский")
    check(any("не найден" in x for x in logs), "про отсутствующий источник сказано")
    check((d1 / "Setup.msi").exists(), "исходная папка не тронута")
    (roots[0] / "extra.txt").write_text("q")
    check(not (d1 / "extra.txt").exists(), "правки в рабочей копии не попадают в исходник")

    # метки дисков
    lab = M.assign_labels(roots, roots[0] / "Setup.msi", ["TRAOD1", "TRAOD2"], [("Release.cab", "TRAOD2"), ("Common.cab", "TRAOD2")])
    check(lab == {roots[0]: "TRAOD1", roots[1]: "TRAOD2"}, f"метки: {lab}")
    lab2 = M.assign_labels(list(reversed(roots)), roots[0] / "Setup.msi", ["TRAOD1", "TRAOD2"], [("Release.cab", "TRAOD2")])
    check(lab2[roots[0]] == "TRAOD1" and lab2[roots[1]] == "TRAOD2", "порядок источников не важен")
    check(M.assign_labels(roots, roots[0] / "Setup.msi", ["A"], [("zzz.cab", "B")]) == {roots[0]: "A"}, "диск без кабинета без метки")
    check(M.safe_label("Диск 1") == "1" or M.safe_label("Диск 1") == "DISC" or M.safe_label("Диск 1").isascii(), "метка латиницей")
    check(M.safe_label("???") == "DISC", "пустая метка -> DISC")
    check(M.disc_root(t / "stg" / "Disc1").name == "TRAOD1", "disc_root заходит во вложенную папку")
    check(M.disc_root(roots[0]) == roots[0], "disc_root не уходит дальше, если там файлы")

# интеграция с portabilizer_v8 (основной конвейер подменён)
import portabilizer_v8 as P
check(str(P.ascii_staging(Path("C:/Игры/x_portable"))).isascii(), "staging латиницей при кириллице в пути")
check(P.ascii_staging(Path("/data/out/x_portable")) == Path("/data/out/x_portable/Extracted_discs"), "staging рядом, если путь латинский")

with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    d1 = t / "d1"; (d1 / "Data").mkdir(parents=True); (d1 / "Setup.msi").write_bytes(b"x")
    d2 = t / "d2"; d2.mkdir(); (d2 / "Release.cab").write_bytes(b"c")
    got = {}
    orig = P._portabilize
    P._portabilize = lambda exe, out, log, mode, mexe, target, job, info: (got.update(exe=Path(exe), target=target, info=dict(info)) or True)
    P.pzp_disc.disc_labels = lambda m: ["TRAOD1", "TRAOD2"]
    logs = []
    info = {"set_target": lambda p: None}
    ok = P._portabilize_multi([d1, d2], t / "out", logs.append, "auto", "", None, info)
    check(ok, "multi вернул True")
    check(got["exe"].name == "Setup.msi" and "Disc1" in str(got["exe"]), f"выбран msi из Disc1: {got['exe']}")
    check(got["target"].name == "d1_portable" and got["target"].is_dir(), "целевая папка создана")
    check((got["target"] / P.MARKER).is_file(), "метка Portabilizer записана")
    check(len(got["info"]["disc_roots"]) == 2 and got["info"]["search_root"].endswith("Extracted_discs"), "диски и search_root переданы в конвейер")
    check(not (got["target"] / "Extracted_discs").exists(), "после успеха рабочая копия дисков удалена")
    check(P._portabilize_multi([d1, d2], t / "out", logs.append, "auto", "", None, dict(info)) is False, "повторный запуск не затирает папку")
    check(P._portabilize_multi([d1, d2], t / "o2", logs.append, "launcher", "", None, dict(info)) is False, "режим launcher не для мультидиска")
    # нет установщика
    e1 = t / "e1"; e1.mkdir(); (e1 / "a.txt").write_text("x"); e2 = t / "e2"; e2.mkdir(); (e2 / "b.txt").write_text("y")
    check(P._portabilize_multi([e1, e2], t / "o3", logs.append, "auto", "", None, dict(info)) is False, "без установщика False")
    check(any("Установщик не найден" in x for x in logs), "про отсутствие установщика сказано")
    P._portabilize = orig
print(f"test_multi: OK ({n} проверок)")
