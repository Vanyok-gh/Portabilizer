"""DirectX-имена ищутся и в dll рядом с exe. Запуск: python tests/test_dx_dir.py"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P

with tempfile.TemporaryDirectory() as t:
    t = Path(t)
    exe = t / "Game.exe"; exe.write_bytes(b"MZ" + b"\0" * 1000)
    assert P.scan_dx_names_dir(exe) == set(), "пустой exe: ничего не найдено"
    (t / "Engine.dll").write_bytes(b"MZ\0\0D3DX9_30.dll\0\0")
    (t / "Other.dll").write_bytes(b"MZ\0\0no names here")
    found = P.scan_dx_names_dir(exe)
    assert found == {"d3dx9_30"}, found
    assert "d3dx9_30" not in P.scan_dx_names(exe), "в самом exe имени нет (воспроизводит баг)"
print("OK: 4 проверок")
