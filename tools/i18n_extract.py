"""Список русских фраз Portabilizer для перевода: python tools/i18n_extract.py [--write]
Берёт все русские строки из portabilizer_v8.py, кроме docstring, регулярных выражений, сравнений и
служебных строк (они остаются русскими). Шаблоны f-строк записываются с {0}, {1}, ... вместо выражений.
Результат: lang/_source.txt (номер<TAB>русская фраза, перенос строки как \\n)."""
import ast, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CYR = re.compile("[А-Яа-яЁё]")
SKIP_CALLS = {"compile", "match", "search", "sub", "findall", "fullmatch", "startswith", "endswith", "find",
              "index", "split", "rsplit", "strip", "lstrip", "rstrip", "replace", "count", "removeprefix",
              "removesuffix", "partition"}


def template(node):
    """JoinedStr -> (шаблон с {0}.., [исходные выражения]) или None, если есть вложенные форматы."""
    parts, exprs = [], []
    for v in node.values:
        if isinstance(v, ast.Constant):
            parts.append(v.value.replace("{", "{{").replace("}", "}}"))
        else:
            if v.format_spec is not None and any(isinstance(x, ast.FormattedValue) for x in v.format_spec.values):
                return None
            spec = ""
            if v.format_spec is not None:
                spec = ":" + "".join(x.value for x in v.format_spec.values)
            conv = {-1: "", 115: "!s", 114: "!r", 97: "!a"}[v.conversion]
            parts.append("{%d%s%s}" % (len(exprs), conv, spec))
            exprs.append(v.value)
    return "".join(parts), exprs


def candidates(tree):
    """Русские строки с признаком, нужно ли их пропустить. Возвращает список (node, text, expr_nodes)."""
    parent = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            parent[c] = p
    doc = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr) \
                and isinstance(n.body[0].value, ast.Constant) and isinstance(n.body[0].value.value, str):
            doc.add(n.body[0].value)
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.JoinedStr):
            t = template(n)
            if t is None or not CYR.search(t[0]):
                continue
            text, exprs = t
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and CYR.search(n.value):
            if isinstance(parent.get(n), (ast.JoinedStr, ast.FormattedValue)):
                continue
            text, exprs = n.value, []
        else:
            continue
        if n in doc:
            continue
        p = parent.get(n)
        skip = False
        while p is not None and not isinstance(p, (ast.stmt,)):
            if isinstance(p, ast.Compare):
                skip = True
            if isinstance(p, ast.Call):
                f = p.func
                name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                if name in SKIP_CALLS and n in p.args:
                    skip = True
            p = parent.get(p)
        if not skip:
            out.append((n, text, exprs))
    return out


def main():
    src = (ROOT / "portabilizer_v8.py").read_text(encoding="utf-8")
    keys = {}
    for n, text, _ in candidates(ast.parse(src)):
        if "@echo off" in text:                 # шаблоны .bat не переводятся
            continue
        keys.setdefault(text, n.lineno)
    print("уникальных фраз:", len(keys), "символов:", sum(len(k) for k in keys))
    if "--write" in sys.argv:
        out = ROOT / "lang"
        out.mkdir(exist_ok=True)
        esc = lambda s: s.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")   # noqa: E731
        (out / "_source.txt").write_text(
            "".join(f"{i}\t{esc(k)}\n" for i, k in enumerate(keys, 1)), encoding="utf-8")


if __name__ == "__main__":
    main()
