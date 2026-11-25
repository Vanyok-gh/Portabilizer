"""Ранжирование exe в папке с кучей файлов (как у Metro): имя игры, 64-бит, служебные утилиты."""
import struct
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


def pe(path: Path, machine=0x014C, subsystem=2, size=2000):
    path.parent.mkdir(parents=True, exist_ok=True)
    b = bytearray(size)
    b[0:2] = b"MZ"
    struct.pack_into("<I", b, 0x3C, 0x80)
    b[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<H", b, 0x84, machine)
    struct.pack_into("<H", b, 0x80 + 24 + 68, subsystem)
    path.write_bytes(bytes(b))


t = Path(tempfile.mkdtemp())

# 1. Имя exe совпадает с названием программы: побеждает без вопросов, хоть рядом файлы и крупнее
d = t / "Metro 2033 Redux" / "App"
pe(d / "metro.exe", size=3000)
pe(d / "MetroConfig.exe", size=9000)
pe(d / "Editor.exe", size=50000)
pe(d / "extras.exe", size=60000)
asked = []
best = P.find_main_exe(d, chooser=lambda o: asked.append(o))
check(best.name == "metro.exe", "metro.exe выбран по имени, а не по размеру")
check(not asked, "вопроса пользователю не было")

# 2. 64-бит предпочтительнее при наличии 32-битной копии
d = t / "Game" / "App"
pe(d / "bin_x86" / "game.exe", machine=0x014C, size=5000)
pe(d / "bin_x64" / "game.exe", machine=0x8664, size=4000)
best = P.find_main_exe(d)
check("bin_x64" in best.parts, "выбрана 64-битная копия")

# 3. 32-битная игра без близнеца не проигрывает 64-битной утилите
d = t / "Old Game" / "App"
pe(d / "oldgame.exe", machine=0x014C, size=5000)
pe(d / "viewer64.exe", machine=0x8664, size=9000)
best = P.find_main_exe(d)
check(best.name == "oldgame.exe", "одиночная 32-битная игра остаётся главной по имени")

# 4. Равные безымянные кандидаты по-прежнему уходят в chooser
d = t / "Zzz" / "App"
pe(d / "alpha.exe", size=3000)
pe(d / "bravo.exe", size=4000)
asked = []
P.find_main_exe(d, chooser=lambda o: asked.append(o) or None)
check(len(asked) == 1, "равные кандидаты - вопрос пользователю")

# 5. Служебные имена не побеждают
d = t / "Prog" / "App"
pe(d / "ProgEditor.exe", size=90000)
pe(d / "prog.exe", size=1000)
check(P.find_main_exe(d).name == "prog.exe", "редактор не главный")

# 6. Раскладка Steam-версии Metro 2033 Redux (по списку файлов depot): metro.exe в корне,
#    pc/redist/D3D11Install/D3D11Install.exe - установщик DirectX, не игра
d = t / "Игра Без Названия" / "App"      # название папки не помогает: имя exe не совпадает с ним
pe(d / "metro.exe", size=21000)
pe(d / "pc/redist/D3D11Install/D3D11Install.exe", machine=0x014C, size=2100)
(d / "content00.vfs0").write_bytes(b"x")
check(P.find_main_exe(d).name == "metro.exe", "Metro: главный metro.exe, а не установщик DirectX")
check(not any("D3D11" in str(x) for x in P.rank_exes(d)), "Metro: D3D11Install отсеян как служебный")
check(P.system_installers(d) == ["pc/redist/D3D11Install/D3D11Install.exe"],
      "Metro: D3D11Install попал в список системных компонентов")

# 7. exe лежит в папке с таким же именем, как он сам: это не повод считать его игрой
d = t / "Another" / "App"
pe(d / "tool" / "tool.exe", size=1000)
pe(d / "run.exe", size=500)
check(P.name_affinity(d / "tool" / "tool.exe", d, ["Another", "App"]) == 0, "собственная папка exe не даёт бонус имени")

# 8. Раскладка Steam-версии S.T.A.L.K.E.R.: Shadow of Chernobyl (depot 4501): bin\\XR_3DA.exe - игра,
#    bin\\dedicated\\XR_3DA.exe - сервер, bin\\testapp.exe - утилита, setup-bp.exe - служебный
for xr, tst in ((3000, 2900), (2900, 3000)):          # размеры почти равны: решать должны не они
    d = Path(tempfile.mkdtemp()) / "Zona" / "App"
    pe(d / "bin" / "XR_3DA.exe", size=xr)
    pe(d / "bin" / "testapp.exe", size=tst)
    pe(d / "bin" / "dedicated" / "XR_3DA.exe", size=2800)
    pe(d / "setup-bp.exe", size=1500)
    asked = []
    best = P.find_main_exe(d, chooser=lambda o: asked.append(o) or None)
    check(best.relative_to(d).as_posix() == "bin/XR_3DA.exe" and not asked,
          f"STALKER: главный bin/XR_3DA.exe без вопросов (размеры {xr}/{tst})")

print("\nпровалов:", len(fails))
sys.exit(1 if fails else 0)
