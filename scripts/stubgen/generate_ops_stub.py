#!/usr/bin/env python
from __future__ import annotations

import ast
from pathlib import Path

from utils import (
    ann_assign,
    build_imports,
    name,
    parse_source_tree,
    scan_module,
    stubify_function_def,
    write_init_pyi,
    write_py_typed,
    write_stub,
)

STUBGEN_DIR = Path(__file__).resolve().parent
ROOT = STUBGEN_DIR.parents[1]

STUB_PATH = ROOT / "stubs" / "tcalc" / "core" / "ops.pyi"
SOURCE_PATH = ROOT / "src" / "tcalc" / "core" / "ops.py"


def _parse_source_tree() -> ast.Module:
    return parse_source_tree(SOURCE_PATH)


def _build_stub_module_ast(
    *,
    header_imports: list[ast.stmt],
    operation_members: list[str],
    properties: list[ast.FunctionDef],
    dataclasses: list[ast.ClassDef],
    public_functions: list[ast.FunctionDef],
    public_typed_constants: list[ast.AnnAssign],
) -> ast.Module:
    header: list[ast.stmt] = [*header_imports]

    function_stubs: list[ast.stmt] = [stubify_function_def(fn) for fn in public_functions]

    op_body: list[ast.stmt] = [
        ast.Assign(
            targets=[ast.Name(id=member, ctx=ast.Store())],
            value=ast.Constant(value=Ellipsis),
        )
        for member in operation_members
    ] + [stubify_function_def(prop) for prop in properties]

    operation_class = ast.ClassDef(
        name="Operation",
        bases=[name("str"), name("Enum")],
        keywords=[],
        body=op_body,
        decorator_list=[],
        type_params=[],
    )

    constants: list[ast.stmt] = [
        ann_assign(const.target.id, annotation=const.annotation, value=None)
        for const in public_typed_constants
    ]

    body = header + dataclasses + function_stubs + [operation_class] + constants

    module = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(module)
    return module


def main() -> int:
    """Generate stub file."""
    try:
        from tcalc.core import ops
    except Exception as exc:
        import sys

        print(f"Failed to import: {exc}", file=sys.stderr)
        return 1

    source_tree = _parse_source_tree()
    scan = scan_module(source_tree)

    # Get enum members from runtime
    members = [op.name for op in ops.Operation]

    stub_module = _build_stub_module_ast(
        header_imports=build_imports(source_tree),
        operation_members=members,
        properties=scan.enum_properties,
        dataclasses=scan.dataclasses,
        public_functions=scan.public_functions,
        public_typed_constants=scan.public_typed_constants,
    )

    # Write stub file
    STUB_PATH.parent.mkdir(parents=True, exist_ok=True)

    stub_pkg_root = ROOT / "stubs" / "tcalc"
    stub_pkg_root.mkdir(parents=True, exist_ok=True)
    write_py_typed(stub_pkg_root)
    write_init_pyi(stub_pkg_root)
    write_init_pyi(STUB_PATH.parent)

    write_stub(STUB_PATH, stub_module, project_root=ROOT)

    print(f"[generate_ops_stub] Wrote {len(members)} ops to {STUB_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
