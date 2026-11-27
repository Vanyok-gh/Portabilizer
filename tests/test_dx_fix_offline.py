"""DX_fix.bat и DX_unpack.ps1 (v11.2): офлайн-распаковка пакета DirectX без запуска установщика.
Константы читаем из исходника без импорта (не нужен Tkinter). PowerShell здесь не запускается:
реальную проверку делает человек на Windows."""
import ast
import re
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "portabilizer_v8.py"
tree = ast.parse(SRC.read_text(encoding="utf-8"))
consts = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        try:
            consts[node.targets[0].id] = ast.literal_eval(node.value)
        except ValueError:
            pass

DX_FIX, PS = consts["DX_FIX"], consts["DX_UNPACK_PS"]
bad = []


def check(cond, msg):
    if not cond:
        bad.append(msg)


bat = (DX_FIX.replace("@DEST@", "App").replace("@URL@", "https://example.invalid/x.exe")
       .replace("@PAGE@", "https://example.invalid/page").replace("@ARCH@", "x64")
       .replace("@FILES@", "xinput1_3.dll x3daudio1_7.dll"))
check(not re.search(r"@[A-Z]+@", bat), "в bat остались подстановки @...@")
check("DX_unpack.ps1" in bat, "bat не вызывает DX_unpack.ps1")
# скачивание только если exe ещё нет, и битый файл после неудачи удаляется
i_have = bat.index('if exist "%EXE%" goto unpack')
i_dl = bat.index("Invoke-WebRequest")
check(i_have < i_dl, "скачивание должно идти после проверки готового exe")
check("Remove-Item" in bat, "после неудачной загрузки битый файл не удаляется")
# порядок: cab из exe без запуска -> запасной /Q /T -> ручная инструкция
check(bat.index("DX_unpack.ps1") < bat.index("/Q /T:") < bat.index(":manual"), "неверный порядок способов распаковки")
# DXSETUP не запускается (в инструкции только упоминается, что запускать его не нужно)
check(not re.search(r'(?im)^\s*"?[^\n]*dxsetup\.exe"?\s*(/|$)', bat.replace("Файл DXSETUP.exe из неё запускать не нужно.", "")),
      "bat запускает DXSETUP.exe")
check("expand.exe *x64.cab" in bat, "извлечение dll из cab пропало")
check("copy /Y" in bat and "xinput1_3.dll" in bat, "копирование dll рядом с игрой пропало")

# PowerShell-скрипт: только ASCII (PS 5.1 читает UTF-8 без BOM как ANSI), баланс скобок, ключевые шаги
check(all(ord(c) < 128 for c in PS), "DX_unpack.ps1 содержит не-ASCII")
for a, b in ("()", "{}", "[]"):
    check(PS.count(a) == PS.count(b), f"несбалансированные {a}{b} в DX_unpack.ps1")
for needle in ("0x4D", "-eq 0x53", "-eq 0x43", "-eq 0x46", "$head[$i+24] -eq 3", "$head[$i+25] -eq 1",
               "ToUInt32", "expand.exe", "Remove-Item"):
    check(needle in PS, f"в DX_unpack.ps1 нет: {needle}")
check(not re.search(r"(?i)dxsetup|Start-Process|Invoke-Expression|\biex\b", PS), "DX_unpack.ps1 не должен запускать процессы кроме expand.exe")

# версия поднята вместе с изменением
check(consts.get("APP_VERSION") == "11.2", f"APP_VERSION = {consts.get('APP_VERSION')}")

if bad:
    print("\n".join("FAIL: " + b for b in bad))
    sys.exit(1)
print("ok: test_dx_fix_offline")
