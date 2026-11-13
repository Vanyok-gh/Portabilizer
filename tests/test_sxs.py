"""pzp_sxs: нужная exe версия Visual C++ 2005/2008, раскладка рядом с игрой. Запуск: python tests/test_sxs.py"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import pzp_sxs as S
import collect_redist as C

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

MAN = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n<assembly xmlns="urn:schemas-microsoft-com:asm.v1" '
       'manifestVersion="1.0"><dependency><dependentAssembly><assemblyIdentity type="win32" name="Microsoft.VC80.CRT" '
       'version="8.0.50727.762" processorArchitecture="x86" publicKeyToken="1fc8b3b9a1e18e3b"></assemblyIdentity>'
       '</dependentAssembly></dependency><dependency><dependentAssembly><assemblyIdentity type="win32" '
       'name="Microsoft.VC90.CRT" version="9.0.21022.8" processorArchitecture="x86" publicKeyToken="1fc8b3b9a1e18e3b">'
       '</assemblyIdentity></dependentAssembly></dependency></assembly>')

with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    game = t / "app"; game.mkdir()
    exe = game / "g.exe"
    exe.write_bytes(b"MZ" + b"\0" * 500 + MAN.encode() + b"\0" * 300)
    need = S.needed(S.exe_manifest(exe))
    check(need == [("Microsoft.VC80.CRT", "8.0.50727.762", "x86"), ("Microsoft.VC90.CRT", "9.0.21022.8", "x86")], f"нужное: {need}")

    dx = t / "dx"; dx.mkdir()
    (dx / "sxs_Microsoft.VC80.CRT_8.0.50727.762_x86.cab").write_bytes(C.cab_write(
        {"msvcr80.dll": b"MZr", "msvcp80.dll": b"MZp", "Microsoft.VC80.CRT.manifest": MAN.encode()}))
    (dx / "sxs_Microsoft.VC80.CRT_8.0.50727.6195_x86.cab").write_bytes(C.cab_write({"x": b"1"}))
    idx = S.sets_index(dx)
    check(len(idx) == 2, "индекс наборов по именам")

    pl = S.plan(exe, dx, winsxs_root=str(t / "nowin"))
    check([k for k, _ in pl["place"]] == [("Microsoft.VC80.CRT", "8.0.50727.762", "x86")], "80 есть в наборах")
    check(pl["missing"] == [("Microsoft.VC90.CRT", "9.0.21022.8", "x86")], "90 в наборах нет - в missing")
    logs = []
    check(S.place(exe, pl, logs.append) == 1, "разложили одну сборку")
    check((game / "msvcr80.dll").read_bytes() == b"MZr" and (game / "Microsoft.VC80.CRT.manifest").is_file(), "файлы рядом")
    pl2 = S.plan(exe, dx, winsxs_root=str(t / "nowin"))
    check(("Microsoft.VC80.CRT", "8.0.50727.762", "x86") in pl2["have"] and not pl2["place"], "повторно не кладём")

    # сборка уже стоит в системе
    ws = t / "win" / "WinSxS" / "x86_microsoft.vc90.crt_1fc8b3b9a1e18e3b_9.0.21022.8_none_abc"
    ws.mkdir(parents=True)
    pl3 = S.plan(exe, dx, winsxs_root=str(t / "win"))
    check(("Microsoft.VC90.CRT", "9.0.21022.8", "x86") in pl3["have"] and not pl3["missing"], "есть в WinSxS - пропуск")

    # exe без манифеста
    e2 = game / "plain.exe"; e2.write_bytes(b"MZ" + b"\0" * 100)
    check(S.plan(e2, dx)["need"] == [], "без манифеста ничего не нужно")
print(f"OK: {n} проверок")
