"""Install_redist.bat: тихие ключи для известных установщиков системных компонентов."""
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


t = Path(tempfile.mkdtemp())
logs = []
ok = P.write_redist_script(t, t / "App", ["_redist\\vcredist_x64.exe", "PhysX\\PhysX_9.exe", "dx\\DXSETUP.exe",
                                          "xnafx40.msi", "msxml6.exe"], logs.append)
txt = (t / "Install_redist.bat").read_text(encoding="utf-8")
check(ok, "скрипт создан")
check('vcredist_x64.exe" /quiet /norestart' in txt, "vcredist: тихий ключ")
check('PhysX_9.exe" /s' in txt, "PhysX: ключ /s")
check('DXSETUP.exe" /silent' in txt, "DirectX: ключ /silent")
check('msiexec /i "%~dp0App\\xnafx40.msi" /qn' in txt, "msi через msiexec")
check("msxml6" not in txt, "неизвестный установщик не попал в скрипт")
check("net session" in txt, "проверка прав администратора")

t2 = Path(tempfile.mkdtemp())
check(not P.write_redist_script(t2, t2 / "App", ["msxml6.exe"], logs.append) and not (t2 / "Install_redist.bat").exists(),
      "только неизвестные - файл не создаётся")

print("\nпровалов:", len(fails))
sys.exit(1 if fails else 0)
