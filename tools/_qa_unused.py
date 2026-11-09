import ast, sys
from pathlib import Path
root = Path("azero")
issues = []
for path in sorted(root.rglob("*.py")) + [Path("main.py")]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imported[(a.asname or a.name).split(".")[0]] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                imported[a.asname or a.name] = node.lineno
    src = path.read_text(encoding="utf-8")
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            pass
    # collect attribute roots
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            n = node
            while isinstance(n, ast.Attribute):
                n = n.value
            if isinstance(n, ast.Name):
                used.add(n.id)
    for name, line in imported.items():
        if name not in used and name != "*":
            issues.append(f"{path}:{line}: unused import {name}")
print("\n".join(issues) if issues else "NO UNUSED IMPORTS")
