"""Однократная правка portabilizer_v8.py: русские строки окна (gui, dx_question) оборачиваются в tr().
Запуск: python tools/i18n_rewrite.py  (повторный запуск ничего не меняет: уже обёрнутые строки пропускаются)."""
import ast, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import i18n_extract as X

ROOT = X.ROOT
SCOPES = {"gui", "dx_question"}
LOG_CALLS = {"log", "ui_log", "base_log"}


def main():
    path = ROOT / "portabilizer_v8.py"
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    starts = [0]
    for ln in lines:
        starts.append(starts[-1] + len(ln.encode("utf-8")))
    raw = src.encode("utf-8")
    parent = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    spans = [(n.lineno, n.end_lineno) for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in SCOPES]

    def inside(n):
        return any(a <= n.lineno <= b for a, b in spans)

    def under_log_or_tr(n):
        p = parent.get(n)
        while p is not None:
            if isinstance(p, ast.Call):
                f = p.func
                name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                if name in LOG_CALLS or name in ("tr", "trx"):
                    return True
            p = parent.get(p)
        return False

    edits, manual = [], []
    for n, text, exprs in X.candidates(tree):
        if not inside(n) or under_log_or_tr(n):
            continue
        a = starts[n.lineno - 1] + n.col_offset
        b = starts[n.end_lineno - 1] + n.end_col_offset
        if isinstance(n, ast.JoinedStr):
            args = "".join(", " + ast.get_source_segment(src, e) for e in exprs)
            new = f"tr({json.dumps(text, ensure_ascii=False)}{args})"
        else:
            new = f"tr({raw[a:b].decode('utf-8')})"
        edits.append((a, b, new))
    # вложенные f-строки с форматами внутри пропущены кандидатами: покажем их
    for n in ast.walk(tree):
        if isinstance(n, ast.JoinedStr) and inside(n) and X.template(n) is None:
            manual.append(n.lineno)
    for a, b, new in sorted(edits, reverse=True):
        raw = raw[:a] + new.encode("utf-8") + raw[b:]
    path.write_bytes(raw)
    print("обёрнуто:", len(edits), "| вручную:", manual)


if __name__ == "__main__":
    main()
