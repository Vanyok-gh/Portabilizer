"""Отчёт после портирования: системные установщики в App и подсказки на типовые сбои.
Запуск: python tests/test_post_report.py"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import portabilizer_v8 as P

n = 0
def check(c, m):
    global n; assert c, "ПРОВАЛ: " + m; n += 1

def tips_for(msg):
    a = P.Advisor()
    a.scan(msg)
    return [(lvl, txt) for _ts, lvl, txt in a.items]

# --- системные установщики
with tempfile.TemporaryDirectory() as t:
    app = Path(t) / "App"
    (app / "_redist").mkdir(parents=True)
    (app / "_redist" / "PhysX_7.05.17_SystemSoftware.exe").write_bytes(b"MZ")
    (app / "_redist" / "vcredist_x86.exe").write_bytes(b"MZ")
    (app / "bin").mkdir()
    (app / "bin" / "Game.exe").write_bytes(b"MZ")
    (app / "bin" / "readme.txt").write_text("x")
    got = P.system_installers(app)
    check(sorted(Path(g).name for g in got) == ["PhysX_7.05.17_SystemSoftware.exe", "vcredist_x86.exe"],
          f"найдены PhysX и vcredist, игра и readme нет: {got}")
    check(P.system_installers(Path(t) / "нет") == [], "несуществующая папка - пусто")
    many = Path(t) / "many"; many.mkdir()
    for i in range(10):
        (many / f"vcredist_{i}.exe").write_bytes(b"MZ")
    check(len(P.system_installers(many)) == 6, "список ограничен шестью")

# --- finish() пишет строку про системные установщики и заметку
with tempfile.TemporaryDirectory() as t:
    tgt = Path(t) / "G_portable"; app = tgt / "App"
    (app / "_redist").mkdir(parents=True)
    (app / "_redist" / "PhysX_SystemSoftware.exe").write_bytes(b"MZ")
    exe = app / "Game.exe"; exe.write_bytes(b"MZ" + b"\0" * 600)
    logs, info = [], {}
    P.finish(tgt, app, exe, logs.append, info, system_root=str(tgt / "noroot"))
    text = "\n".join(logs)
    check("установщики системных компонентов: _redist" in text.replace("\\", "/") or
          "установщики системных компонентов" in text, "строка про системные установщики в логе")
    check(any("системных компонентов" in x for x in info.get("notes", [])), "заметка в итоговом отчёте")
    check(tips_for("Внутри App лежат установщики системных компонентов: _redist\\x.exe")[0][0] == "info",
          "подсказка в панели появляется")

with tempfile.TemporaryDirectory() as t:
    tgt = Path(t) / "G_portable"; app = tgt / "App"; app.mkdir(parents=True)
    exe = app / "Game.exe"; exe.write_bytes(b"MZ" + b"\0" * 600)
    logs, info = [], {}
    P.finish(tgt, app, exe, logs.append, info, system_root=str(tgt / "noroot"))
    check(not any("системных компонентов" in x for x in logs), "без установщиков строки нет")

# --- правила на сбои, раньше молчавшие
r = tips_for("Установщик не найден ни на одном диске. Проверьте, что выбраны все диски игры.")
check(r and r[0][0] == "warn" and "Extracted_discs" in r[0][1], f"подсказка: установщик не найден на дисках: {r}")
r = tips_for("В папке нет установщика (msi, Inno, NSIS, WiX). Готовые папки приложений пока не поддерживаются")
check(r and "Extracted_discs" in r[0][1], "подсказка: в папке нет установщика")
r = tips_for("Установка не удалась - распакованные файлы возвращены в App.")
check(r and r[0][0] == "warn" and "администратора" in r[0][1], "подсказка: установка не удалась")
check(tips_for("Всё хорошо, Готово: C:\\x") == [], "на успешные сообщения подсказок нет")

print(f"OK: {n} проверок")
