"""DX_fix.bat учитывает разрядность и кладёт только нужные файлы; dx_dir находит папку. Запуск: python tests/test_dx_fix.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P
bat = P.DX_FIX
assert "@ARCH@" in bat and "@FILES@" in bat and "x64" not in bat, "шаблон не зависит от x64"
out = bat.replace("@ARCH@", "x86").replace("@FILES@", "d3dx9_30.dll")
assert "*x86.cab" in out and "for %%F in (d3dx9_30.dll)" in out and "*.dll" in out
assert "@" not in out.replace("@echo", "").replace("@URL@", "").replace("@PAGE@", "").replace("@DEST@", ""), "остались подстановки"
assert P.dx_dir().name == "dx"
print("OK: 4 проверок")
