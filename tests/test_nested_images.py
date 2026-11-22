"""Архив с образами дисков внутри (find_disc_images + ветка архива в _portabilize). Запуск: python tests/test_nested_images.py"""
import sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

MB = b"\0" * (1024 * 1024)

# --- поиск образов и порядок дисков
with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    for name in ("Game Disc 10.ISO", "Game Disc 2.ISO", "Game Disc 1.ISO"):
        (t / name).write_bytes(MB)
    (t / "tiny.iso").write_bytes(b"x")                 # слишком маленький: не диск
    (t / "readme.txt").write_text("x")
    deep = t / "a" / "b" / "c" / "d"; deep.mkdir(parents=True); (deep / "Disc 9.iso").write_bytes(MB)
    got = [p.name for p in P.find_disc_images(t)]
    check(got == ["Game Disc 1.ISO", "Game Disc 2.ISO", "Game Disc 10.ISO"], f"порядок дисков по числам: {got}")
    check(P.find_disc_images(t / "нет") == [], "несуществующая папка - пусто")

# --- архив без exe и установщика, внутри три образа
with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    z = t / "game_202504.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for i in (1, 2, 3):
            zf.writestr(f"Game Disc {i}.ISO", MB)
        zf.writestr("meta.xml", "<x/>")
    seen = {}

    def fake_extract(f, kind, out, log, job=None):
        out = Path(out); out.mkdir(parents=True, exist_ok=True)
        f = Path(f)
        if f.suffix.lower() == ".iso":               # «распаковка» образа: на диске 1 лежит установщик
            (out / "Setup.msi").write_bytes(b"x" if f.name.endswith("1.ISO") else b"")
            (out / f"{f.stem.replace(' ', '_')}.dat").write_bytes(b"d")
            return True
        zipfile.ZipFile(f).extractall(out)
        return True

    orig_extract, orig_port = P.extract, P._portabilize
    def fake_port(exe, out, log, mode, mexe, target, job, info):
        if Path(exe).suffix.lower() == ".msi":
            seen.update(exe=Path(exe), target=target, discs=[Path(r).name for r in info.get("disc_roots", [])])
            return True
        return orig_port(exe, out, log, mode, mexe, target, job, info)
    P.extract, P._portabilize = fake_extract, fake_port
    # find_disc_msi/find_installer смотрят на тип msi: пустые msi на дисках 2-3 не должны выбираться первыми
    P.pzp_disc.is_disc_msi = lambda p: False
    logs = []
    info = {"set_target": lambda p: None}
    out = t / "out"; out.mkdir()
    try:
        ok = P._portabilize(str(z), out, logs.append, "auto", "", None, None, info)
    finally:
        P.extract, P._portabilize = orig_extract, orig_port
    text = "\n".join(logs)
    check(ok is True, f"архив с образами обработан: {text}")
    check("образы дисков" in text, "в логе сказано про образы дисков")
    check(len(seen.get("discs", [])) == 3, f"передано три диска: {seen}")
    check(seen["exe"].name == "Setup.msi", "найден установщик с диска")
    check((out / "game_202504_portable" / "Extracted_archive" / "Game Disc 1.ISO").is_file(),
          "исходные образы сохранены в Extracted_archive")
    check("Main exe" not in text and "Главный exe не найден" not in text, "ошибки про главный exe нет")

print(f"OK: {n} проверок")
