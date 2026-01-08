#!/usr/bin/env python
from __future__ import annotations

import ast
import sys
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

STUB_PATH = ROOT / "stubs" / "tcalc" / "core" / "ops.pyi"
SOURCE_PATH = ROOT / "src" / "tcalc" / "core" / "ops.py"


def parse_ui_op_spec_class() -> str:
    """Parse _UIOpSpec class definition from source code."""
    tree = ast.parse(SOURCE_PATH.read_text())
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "_UIOpSpec":
            return ast.unparse(node)
    return ""


def parse_properties() -> list[tuple[str, str]]:
    """Parse OperationBase properties from source code."""
    tree = ast.parse(SOURCE_PATH.read_text())
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "OperationBase":
            props = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and any(
                    isinstance(d, ast.Name) and d.id == "property" for d in item.decorator_list
                ):
                    ret_type = ast.unparse(item.returns) if item.returns else "object"
                    props.append((item.name, ret_type))
            return sorted(props)
    return []


def main() -> int:
    """Generate stub file."""
    try:
        from tcalc.core import ops
    except Exception as exc:
        print(f"Failed to import: {exc}", file=sys.stderr)
        return 1

    # Get enum members from runtime
    members = [op.name for op in ops.Operation]
    
    # Get properties from source
    properties = parse_properties()
    
    # Get _UIOpSpec class definition from source
    ui_op_spec_class = parse_ui_op_spec_class()

    # Generate stub content
    lines = [
        dedent("""
            from __future__ import annotations
            
            from dataclasses import dataclass
            from enum import Enum
            from typing import Callable, TypeAlias
            
            import calc_native
            
            OpId: TypeAlias = calc_native.OpId
            OpSpec: TypeAlias = calc_native.OpSpec
        """).strip()
    ]
    
    # Add _UIOpSpec class from source
    if ui_op_spec_class:
        lines.append("")
        lines.append(ui_op_spec_class)
    
    lines.append("")
    lines.append("class Operation(str, Enum):")
    
    # Add enum members
    for name in members:
        lines.append(f"    {name} = ...")
    
    # Add properties
    for prop_name, ret_type in properties:
        lines.append("")
        lines.append("    @property")
        lines.append(f"    def {prop_name}(self) -> {ret_type}: ...")
    
    # Add module-level items
    lines.extend([
        "",
        "OP_BY_ID: dict[OpId, OpSpec]",
        "PROMO_RULES_BY_ID: dict[OpId, Callable[..., bool]]",
        "",
        "def get_symbols_with_aliases(filter_fn: Callable[[OpSpec | _UIOpSpec], bool] | None = None) -> set[str]: ...",
        "",
    ])
    
    # Write stub file
    stub_pkg_root = STUB_PATH.parents[1]
    stub_pkg_root.mkdir(parents=True, exist_ok=True)
    (stub_pkg_root / "py.typed").write_text("partial\n", encoding="utf-8")
    (stub_pkg_root / "__init__.pyi").parent.mkdir(parents=True, exist_ok=True)
    if not (stub_pkg_root / "__init__.pyi").exists():
        (stub_pkg_root / "__init__.pyi").write_text("from __future__ import annotations\n", encoding="utf-8")
    STUB_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rel = STUB_PATH.relative_to(Path.cwd())
    print(f"[generate_ops_stub] Wrote {len(members)} ops to {STUB_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
