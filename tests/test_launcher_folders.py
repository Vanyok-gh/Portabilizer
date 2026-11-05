"""Launch.bat создаёт в Data стандартные папки пользователя. Запуск: python tests/test_launcher_folders.py"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P
t = Path(tempfile.mkdtemp()) / "X_portable"; a = t / "App"; a.mkdir(parents=True); (a / "x.exe").write_bytes(b"MZ")
P.finish(t, a, a / "x.exe", lambda s: None, {}, system_root=str(t / "noroot"))
bat = (t / "Launch.bat").read_text("utf-8")
line = next(l for l in bat.splitlines() if l.startswith("for %%D in ("))
for d in ("Desktop", "Downloads", "Music", "Pictures", "Videos", '"Saved Games"'):
    assert d in line, d
assert 'mkdir "%DATA%\\%%~D"' in line and "{" not in bat and "@" not in bat.split("start")[0].replace("@echo", ""), "шаблон"
assert bat.index("USERPROFILE=") > bat.index("for %%D"), "папки создаются до подмены профиля"
print("папки пользователя в Launch.bat: ок")
