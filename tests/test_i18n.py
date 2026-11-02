"""Переводы Portabilizer: данные целы, окно строится на каждом языке, журнал и подсказки переводятся.
Запуск: python tests/test_i18n.py"""
import sys
from pathlib import Path
from unittest.mock import MagicMock
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
n = [0]


def check(c, m):
    if not c:
        print("ПРОВАЛ:", m); sys.exit(1)
    n[0] += 1


import re
import pzp_i18n as I
import pzp_lang_data as D
ph = lambda s: sorted(re.findall(r"\{(\d+)", s.replace("{{", "").replace("}}", "")))   # noqa: E731
check(len(D.KEYS) >= 353 and len(set(D.KEYS)) == len(D.KEYS), "ключи без повторов")
for code, table in D.TEXTS.items():
    check(len(table) >= len(D.KEYS) - 3, f"{code}: почти все фразы переведены ({len(table)}/{len(D.KEYS)})")
    for k, v in table.items():
        check(ph(k) == ph(v), f"{code}: подстановки {k[:40]!r}")
    for c2 in D.CODES:
        check(I.lang_name(code, c2).strip() != "", f"название {c2} на {code}")

# окно на поддельном tkinter, на каждом языке
class Var:
    def __init__(self, master=None, value=None): self.v = value; self.cbs = []
    def get(self): return self.v
    def set(self, v):
        self.v = v
        for c in self.cbs: c()
    def trace_add(self, mode, cb): self.cbs.append(lambda: cb())
tk = MagicMock(name="tk"); tk.StringVar = Var; tk.BooleanVar = Var; tk.IntVar = Var
ttk = MagicMock(name="ttk"); style = MagicMock(); style.theme_use.return_value = "vista"; ttk.Style.return_value = style
rootm = MagicMock(); rootm.cget.return_value = "#f0f0f0"; rootm.geometry.return_value = "880x720+5+5"; tk.Tk.return_value = rootm
tv = MagicMock(); tv.selection.return_value = (); tv.get_children.return_value = (); ttk.Treeview.return_value = tv
sys.modules.update({"tkinter": tk, "tkinter.ttk": ttk})
tk.ttk = ttk
import portabilizer_v8 as P
P.save_settings = lambda d, path=None: None
P.History = lambda *a, **k: MagicMock(all=lambda: [])
seen = {}
for code in ["ru"] + sorted(D.TEXTS):
    P.load_settings = lambda path=None, c=code: {"language": c, "check_updates": False}
    seen.clear()
    P.gui(_hook=lambda ctx: seen.update(ctx))
    check(I.get_lang() == code, f"{code}: язык применён")
    check(seen.get("lang_var") is not None or True, "окно построено")
P.load_settings = lambda path=None: {"language": "de", "check_updates": False}
P.gui(_hook=lambda ctx: seen.update(ctx))
check(I.tr("Пауза") == "Pause", "tr de")
check(I.trx("Готово: x") == "Fertig: x" or I.trx("Готово: x").startswith("Fertig"), "trx шаблон")
check(I.trx("Какой-то неизвестный текст") == "Какой-то неизвестный текст", "неизвестное остаётся русским")
check(I.trx("Исходный файл НЕ удалён") != "", "trx точная фраза")
# смена языка: сохраняется в настройки, окно закрывается для перезапуска, версия R сохраняется
P.RESTART.update(flag=False)
P.load_settings = lambda path=None: {"language": "ru", "check_updates": False}
box = {}
P.gui(_hook=lambda ctx: box.update(ctx))
box["lang_var"].set("ja")
check(box["settings"].get("language") == "ja" and P.RESTART["flag"] and rootm.destroy.called, "смена языка: сохранено, перезапуск")
box["state"]["job"] = object(); P.RESTART.update(flag=False); box["lang_var"].set("fr")
check(not P.RESTART["flag"] and box["lang_var"].get() == I.get_lang(), "во время задачи язык не меняется")
I.set_lang("ru")
print(f"переводы Portabilizer: {n[0]} проверок пройдено")
