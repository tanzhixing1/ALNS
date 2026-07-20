from __future__ import annotations

import ast
import csv
import json
from pathlib import Path
from typing import Any


OUTPUT = Path(__file__).resolve().parent
ROOTS = {
    "baseline": Path(r"D:\STUDY\game\github-program\noteread\ALNS_worktrees\stage2f2a_baseline\tvdctp_c_alns"),
    "current": Path(r"D:\STUDY\game\github-program\noteread\ALNS_worktrees\stage2f2a_current\tvdctp_c_alns"),
}


def phase_for(file: str, function: str, kind: str) -> str:
    if kind in {"definition", "import"}:
        return kind
    if file == "alns_solver.py" and function == "run_c_alns":
        return "solver initial/final validation"
    if file == "objective.py":
        return "objective feasibility boundary"
    if file == "initial_solution.py":
        return "initial construction/final validation"
    if file == "operators.py" and function == "_validate_cascade_candidate":
        return "Cascade repair candidate validation"
    if file == "operators.py":
        return "repair/consolidation boundary"
    if file == "evaluation.py":
        return "evaluation/final output validation"
    if file == "diagnose_calns.py":
        return "diagnostic final validation"
    if file.startswith("tests/"):
        return "test-side direct validation/instrumentation"
    return "other"


class Visitor(ast.NodeVisitor):
    def __init__(self, relative_file: str) -> None:
        self.relative_file = relative_file
        self.stack: list[str] = []
        self.rows: list[dict[str, Any]] = []

    @property
    def function(self) -> str:
        return self.stack[-1] if self.stack else "<module>"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name == "check_solution_feasible":
            self.rows.append(self.row(node.lineno, "definition", "definition", node.name))
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "feasibility":
            for alias in node.names:
                if alias.name == "check_solution_feasible":
                    bound = alias.asname or alias.name
                    self.rows.append(self.row(node.lineno, "import", "alias", bound))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        callee = None
        direct = None
        if isinstance(node.func, ast.Name) and node.func.id == "check_solution_feasible":
            callee = node.func.id
            direct = "direct imported reference"
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "check_solution_feasible":
            callee = ast.unparse(node.func)
            direct = "direct module attribute"
        if callee is not None:
            self.rows.append(self.row(node.lineno, "call", direct, callee))
        self.generic_visit(node)

    def row(self, line: int, kind: str, direct: str, callee: str) -> dict[str, Any]:
        return {
            "file": self.relative_file,
            "function": self.function,
            "line": line,
            "kind": kind,
            "direct_indirect": direct,
            "callee": callee,
            "phase": phase_for(self.relative_file, self.function, kind),
        }


def scan(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.py")):
        relative = str(path.relative_to(root)).replace("\\", "/")
        if relative.startswith("outputs/"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        visitor = Visitor(relative)
        visitor.visit(tree)
        rows.extend(visitor.rows)
    return rows


def stable_id(row: dict[str, Any]) -> tuple[str, str, str, str, int]:
    return (
        row["file"],
        row["function"],
        row["kind"],
        row["callee"],
        0,
    )


def main() -> None:
    scans = {version: scan(root) for version, root in ROOTS.items()}
    grouped: dict[tuple[str, str, str, str, int], dict[str, Any]] = {}
    for version, rows in scans.items():
        occurrences: dict[tuple[str, str, str, str], int] = {}
        for row in rows:
            base = (row["file"], row["function"], row["kind"], row["callee"])
            occurrences[base] = occurrences.get(base, 0) + 1
            key = (*base, occurrences[base])
            combined = grouped.setdefault(
                key,
                {
                    "Call Site ID": "",
                    "File": row["file"],
                    "Function": row["function"],
                    "Direct/Indirect": row["direct_indirect"],
                    "Phase": row["phase"],
                    "Baseline": "ABSENT",
                    "Current": "ABSENT",
                    "Notes": f"{row['kind']}: {row['callee']}",
                },
            )
            combined[version.capitalize()] = f"line {row['line']}"

    output_rows = []
    for index, (_, row) in enumerate(sorted(grouped.items()), start=1):
        row["Call Site ID"] = f"CCS-{index:03d}"
        output_rows.append(row)
    fields = [
        "Call Site ID",
        "File",
        "Function",
        "Direct/Indirect",
        "Phase",
        "Baseline",
        "Current",
        "Notes",
    ]
    with (OUTPUT / "03a_checker_callsite_inventory.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)
    (OUTPUT / "checker_callsite_inventory.json").write_text(
        json.dumps(
            {"roots": {key: str(value) for key, value in ROOTS.items()}, "rows": output_rows},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
