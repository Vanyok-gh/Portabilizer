"""Собирает pzp_lang_data.py из lang/*.txt. Запуск: python tools/make_lang.py
Тексты: lang/<код>.txt (номер<TAB>перевод; номера - из lang/_source.txt, ключ - русская фраза),
названия языков: lang/<код>_names.txt. Править нужно txt-файлы, не pzp_lang_data.py."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
L = root / "lang"


def unesc(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s) and s[i + 1] in "nt\\":
            out.append({"n": "\n", "t": "\t", "\\": "\\"}[s[i + 1]]); i += 2
        else:
            out.append(s[i]); i += 1
    return "".join(out)


src = {}
for line in (L / "_source.txt").read_text(encoding="utf-8").splitlines():
    n, ru = line.split("\t", 1); src[n] = unesc(ru)
codes = [l.split("\t")[0] for l in (L / "_codes.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
texts, names = {}, {}
for c in codes:
    f = L / f"{c}.txt"
    if f.exists():
        rows = dict(l.split("\t", 1) for l in f.read_text(encoding="utf-8").splitlines() if l.strip())
        texts[c] = {src[n]: unesc(rows[n]) for n in src if rows.get(n, "").strip()}
    f = L / f"{c}_names.txt"
    if f.exists():
        names[c] = dict(l.split("\t", 1) for l in f.read_text(encoding="utf-8").splitlines() if l.strip())
out = ['"""Сгенерировано tools/make_lang.py из lang/*.txt. Не править вручную."""\n',
       f"CODES = {tuple(codes)!r}\n", f"KEYS = {tuple(src.values())!r}\n", "TEXTS = {\n"]
for c, d in texts.items():
    out.append(f"    {c!r}: {{\n")
    out += [f"        {k!r}: {v!r},\n" for k, v in d.items()]
    out.append("    },\n")
out.append("}\nNAMES = {\n")
for c, d in names.items():
    out.append(f"    {c!r}: {d!r},\n")
out.append("}\n")
(root / "pzp_lang_data.py").write_text("".join(out), encoding="utf-8")
print("языков с текстом:", len(texts), "с названиями:", len(names), "фраз:", len(src))
