"""Языки интерфейса Portabilizer. Русский текст в коде - ключ перевода.

tr("фраза {0}", x)  - перевод фразы; подстановки {0}, {1}, ... (как str.format).
trx(текст)          - перевод готовой строки (строки журнала, подсказки, заметки): сначала точное
                      совпадение, потом по шаблонам f-строк. Незнакомый текст остаётся русским.
Данные лежат в pzp_lang_data.py (сборка: python tools/make_lang.py из lang/*.txt).
"""
import locale
import re

try:
    from pzp_lang_data import CODES, KEYS, NAMES, TEXTS
except ImportError:                                      # без данных интерфейс остаётся русским
    CODES, KEYS, NAMES, TEXTS = ("ru",), (), {}, {}

LANGS = tuple((c, NAMES.get(c, {}).get(c, c)) for c in CODES if c == "ru" or c in TEXTS)
_cur = {"lang": "ru", "cache": {}}
_PH = re.compile(r"\{(\d+)(?:![sra])?(?::[^{}]*)?\}")
_TPL = []                                                # [(regex, ключ)] для ключей с подстановками


def _build():
    items = []
    for k in KEYS:
        if "{" not in k:
            continue
        parts, pos, n = [], 0, 0
        for m in _PH.finditer(k):
            parts.append(re.escape(k[pos:m.start()].replace("{{", "{").replace("}}", "}")))
            parts.append("(.*?)")
            pos, n = m.end(), n + 1
        if not n:
            continue
        parts.append(re.escape(k[pos:].replace("{{", "{").replace("}}", "}")))
        lit = len(k) - sum(m.end() - m.start() for m in _PH.finditer(k))
        items.append((lit, re.compile("".join(parts), re.S), k))
    items.sort(key=lambda t: -t[0])                       # сначала самые определённые шаблоны
    _TPL[:] = [(rx, k) for _, rx, k in items]


def set_lang(code):
    _cur["lang"] = code if code == "ru" or code in TEXTS else "ru"
    _cur["cache"] = {}
    if not _TPL and KEYS:
        _build()
    return _cur["lang"]


def get_lang() -> str:
    return _cur["lang"]


def detect_lang() -> str:
    try:
        loc = (locale.getlocale()[0] or locale.getdefaultlocale()[0] or "")[:2].lower()
    except Exception:                                    # noqa: BLE001
        loc = ""
    loc = {"nb": "no", "nn": "no"}.get(loc, loc)
    return loc if loc in TEXTS else "en" if "en" in TEXTS else "ru"


def lang_name(ui: str, code: str) -> str:
    return NAMES.get(ui, {}).get(code) or NAMES.get(code, {}).get(code, code)


def _fill(text, groups):
    out = _PH.sub(lambda m: groups[int(m.group(1))] if int(m.group(1)) < len(groups) else m.group(0), text)
    return out.replace("{{", "{").replace("}}", "}")


def tr(key: str, *args, **kw) -> str:
    text = key
    if _cur["lang"] != "ru":
        text = TEXTS.get(_cur["lang"], {}).get(key) or key
    return text.format(*args, **kw) if (args or kw) else text


def trx(s):
    """Перевод готовой строки (см. модуль)."""
    lang = _cur["lang"]
    if lang == "ru" or not isinstance(s, str) or not s:
        return s
    cache = _cur["cache"]
    if s in cache:
        return cache[s]
    table = TEXTS.get(lang, {})
    res = table.get(s)
    if res is None:
        for rx, key in _TPL:
            m = rx.fullmatch(s)
            if m and table.get(key):
                res = _fill(table[key], m.groups())
                break
    if res is None:                                      # многострочный текст: переводим построчно
        if "\n" in s:
            res = "\n".join(trx(x) for x in s.split("\n"))
        else:
            res = s
    cache[s] = res
    return res
