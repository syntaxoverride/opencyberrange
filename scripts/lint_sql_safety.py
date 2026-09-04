#!/usr/bin/env python3
"""Fail on string-built SQL in the backend (regression guard for finding I1).

Raw SQL must use bound parameters (SQLAlchemy ``text("... :name")`` + a params
dict), never Python string interpolation. This AST check flags any ``text(...)``
or ``.execute(...)`` / ``.exec_driver_sql(...)`` whose SQL argument is built with
an f-string, ``.format()``, ``%``, or ``+`` on a non-constant -- the shapes that
turn user input into SQL injection.

Usage:  python scripts/lint_sql_safety.py [root]   (default: platform/backend/app)
Exit 1 if any violation is found.
"""
import ast
import os
import sys

EXEC_METHODS = {"execute", "exec_driver_sql", "executemany"}


def _sql_sink(call: ast.Call) -> str | None:
    """Return a label if this call is a SQL sink, else None.

    Bare ``text(...)`` is SQLAlchemy's text(); ``.execute``/``.exec_driver_sql``/
    ``.executemany`` are DB-API/SQLAlchemy execs. We deliberately do NOT match a
    ``.text`` attribute call (e.g. matplotlib ``ax.text(...)``).
    """
    f = call.func
    if isinstance(f, ast.Name) and f.id == "text":
        return "text"
    if isinstance(f, ast.Attribute) and f.attr in EXEC_METHODS:
        return f.attr
    return None


def _is_dynamic(node: ast.AST) -> bool:
    """True if the SQL-string node is assembled from non-constant pieces."""
    if isinstance(node, ast.JoinedStr):  # f-string
        return any(isinstance(v, ast.FormattedValue) for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mod, ast.Add)):
        # "..." % x  or  "..." + x  where a side is not a plain constant
        return not (isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant))
    if isinstance(node, ast.Call):  # "...".format(...)
        return isinstance(node.func, ast.Attribute) and node.func.attr == "format"
    return False


def scan_file(path: str) -> list[tuple[int, str]]:
    try:
        src = open(path, encoding="utf-8").read()
        tree = ast.parse(src)
    except (SyntaxError, UnicodeDecodeError) as exc:
        return [(0, f"parse error: {exc}")]
    lines = src.splitlines()
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        sink = _sql_sink(node)
        if sink is None:
            continue
        if _is_dynamic(node.args[0]):
            # Inline escape hatch for the rare legitimate case: DDL with constant
            # identifiers (column/table names can't be bound parameters). Mark the
            # line with '# sql-safe' and a reason.
            line_txt = lines[node.lineno - 1] if 0 < node.lineno <= len(lines) else ""
            if "# sql-safe" in line_txt:
                continue
            hits.append((node.lineno, sink))
    return hits


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "platform", "backend", "app",
    )
    findings = []
    for dirpath, _dirs, files in os.walk(root):
        if "__pycache__" in dirpath:
            continue
        for fn in files:
            if fn.endswith(".py"):
                p = os.path.join(dirpath, fn)
                for line, callee in scan_file(p):
                    findings.append((os.path.relpath(p, root), line, callee))
    if findings:
        print("SQL-safety lint FAILED: string-built SQL (use bound :params instead)\n")
        for rel, line, callee in sorted(findings):
            print(f"  {rel}:{line}  interpolated SQL passed to {callee}(...)")
        print(f"\n{len(findings)} violation(s).")
        return 1
    print("SQL-safety lint passed: no string-built SQL found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
