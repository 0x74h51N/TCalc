#!/usr/bin/env python
from __future__ import annotations

"""
Generate a static typing stub for tcalc.core.ops.Operation from the current runtime data.
"""

from dataclasses import fields, MISSING
from pathlib import Path
from textwrap import dedent
import sys
import inspect
import ast


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

STUB_PATH = ROOT / "stubs" / "tcalc" / "core" / "ops.pyi"
OPS_SOURCE_PATH = ROOT / "src" / "tcalc" / "core" / "ops.py"


def _format_default(field_default: object) -> str:
    return " = ..." if field_default is not MISSING else ""


def _iter_operation_properties(operation_type: type) -> list[tuple[str, str]]:
    props: list[tuple[str, str]] = []
    for name, attr in inspect.getmembers(operation_type):
        if not isinstance(attr, property):
            continue
        fget = attr.fget
        if fget is None:
            continue
        ann = getattr(fget, "__annotations__", {})
        ret = ann.get("return")
        if ret is None:
            ret_str = "object"
        else:
            ret_str = str(ret)
        props.append((name, ret_str))
    props.sort(key=lambda x: x[0])
    return props


def _parse_operation_property_returns(source_path: Path) -> list[tuple[str, str]]:
    module = ast.parse(source_path.read_text(encoding="utf-8"))
    for stmt in module.body:
        if not isinstance(stmt, ast.ClassDef) or stmt.name != "OperationBase":
            continue

        props: list[tuple[str, str]] = []
        for item in stmt.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            if not any(isinstance(d, ast.Name) and d.id == "property" for d in item.decorator_list):
                continue
            if item.returns is None:
                ret = "object"
            else:
                ret = ast.unparse(item.returns)
            props.append((item.name, ret))

        props.sort(key=lambda x: x[0])
        return props

    return []


def main() -> int:
    try:
        from tcalc.core import ops
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        print(f"[generate_ops_stub] Failed to import tcalc.core.ops: {exc}", file=sys.stderr)
        return 1

    members = [(op.name, op.value) for op in ops.Operation]
    spec_fields = fields(ops.OpSpec)
    op_props = _parse_operation_property_returns(OPS_SOURCE_PATH)
    if not op_props:
        op_props = _iter_operation_properties(ops.Operation)

    header = dedent(
        """
        from __future__ import annotations

        from dataclasses import dataclass
        from enum import Enum
        from typing import Callable

        import calc_native

        OpId = calc_native.OpId

        @dataclass(frozen=True, slots=True)
        class OpSpec:
        """
    ).strip("\n")

    lines: list[str] = [header]
    for f in spec_fields:
        lines.append(f"    {f.name}: {f.type}{_format_default(f.default)}")

    lines.append("")
    lines.append("class Operation(str, Enum):")
    lines.append("    _spec: OpSpec")
    for name, _value in members:
        lines.append(f"    {name} = ...")

    for prop_name, ret in op_props:
        lines.append("")
        lines.append("    @property")
        lines.append(f"    def {prop_name}(self) -> {ret}: ...")

    lines.append("")
    lines.append("OP_BY_ID: dict[OpId, OpSpec]")
    lines.append("")
    lines.append(
        "def get_symbols_with_aliases(filter_fn: Callable[[OpSpec], bool] | None = None) -> set[str]: ..."
    )
    lines.append("")

    STUB_PATH.parent.mkdir(parents=True, exist_ok=True)
    stub_pkg_root = STUB_PATH.parents[1]
    stub_pkg_root.mkdir(parents=True, exist_ok=True)
    (stub_pkg_root / "py.typed").write_text("partial\n", encoding="utf-8")
    for pkg_init in (stub_pkg_root / "__init__.pyi", stub_pkg_root / "core" / "__init__.pyi"):
        pkg_init.parent.mkdir(parents=True, exist_ok=True)
        if not pkg_init.exists():
            pkg_init.write_text("from __future__ import annotations\n", encoding="utf-8")
    STUB_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rel = STUB_PATH.relative_to(Path.cwd())
    print(f"[generate_ops_stub] Wrote {len(members)} ops to {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
