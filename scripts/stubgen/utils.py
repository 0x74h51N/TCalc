from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from subprocess import run


def parse_source_tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def find_top_level_class(tree: ast.Module, name: str) -> ast.ClassDef | None:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    return None


def has_property_decorator(fn: ast.FunctionDef) -> bool:
    return any(isinstance(d, ast.Name) and d.id == "property" for d in fn.decorator_list)


def name(id_: str) -> ast.Name:
    return ast.Name(id=id_, ctx=ast.Load())


def attr(value: ast.expr, attr_name: str) -> ast.Attribute:
    return ast.Attribute(value=value, attr=attr_name, ctx=ast.Load())


def ann_assign(name_str: str, annotation: ast.expr, value: ast.expr | None = None) -> ast.AnnAssign:
    return ast.AnnAssign(
        target=ast.Name(id=name_str, ctx=ast.Store()),
        annotation=annotation,
        value=value,
        simple=1,
    )


def expr_stmt(expr: ast.expr) -> ast.stmt:
    return ast.Expr(value=expr)


def build_imports(tree: ast.Module) -> list[ast.stmt]:
    header: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            header.append(
                ast.Import(
                    names=[ast.alias(name=a.name, asname=a.asname) for a in node.names],
                )
            )
        elif isinstance(node, ast.ImportFrom):
            header.append(
                ast.ImportFrom(
                    module=node.module,
                    names=[ast.alias(name=a.name, asname=a.asname) for a in node.names],
                    level=node.level,
                )
            )
    return header


FUTURE_ANNOTATIONS = "from __future__ import annotations\n"


def write_init_pyi(package_dir: Path, *, content: str = FUTURE_ANNOTATIONS) -> None:
    init_pyi = package_dir / "__init__.pyi"
    if not init_pyi.exists():
        init_pyi.write_text(content, encoding="utf-8")


def write_py_typed(package_dir: Path, *, content: str = "partial\n") -> None:
    (package_dir / "py.typed").write_text(content, encoding="utf-8")


def run_ruff_format(path: Path, *, project_root: Path | None = None) -> None:
    ruff_bin = which("ruff")
    if ruff_bin is None and project_root is not None:
        ruff_bin = str(project_root / "venv" / "bin" / "ruff")
    if ruff_bin and Path(ruff_bin).exists():
        run([ruff_bin, "format", str(path)], check=False)


def stubify_function_def(fn: ast.FunctionDef) -> ast.FunctionDef:
    return ast.FunctionDef(
        name=fn.name,
        args=fn.args,
        body=[expr_stmt(ast.Constant(value=Ellipsis))],
        decorator_list=fn.decorator_list,
        returns=fn.returns,
        type_comment=None,
    )


def write_stub(path: Path, module: ast.Module, *, project_root: Path | None = None) -> None:
    stub_text = ast.unparse(module).rstrip() + "\n"
    path.write_text(stub_text, encoding="utf-8")
    run_ruff_format(path, project_root=project_root)


@dataclass(frozen=True, slots=True)
class ModuleScan:
    dataclasses: list[ast.ClassDef]
    public_functions: list[ast.FunctionDef]
    public_typed_constants: list[ast.AnnAssign]
    enum_properties: list[ast.FunctionDef]


def scan_module(tree: ast.Module) -> ModuleScan:
    dataclasses_: list[ast.ClassDef] = []
    public_functions: list[ast.FunctionDef] = []
    public_typed_constants: list[ast.AnnAssign] = []
    best_enum_properties: list[ast.FunctionDef] = []
    best_enum_properties_count = 0

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            is_dataclass = False
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name) and dec.id == "dataclass":
                    is_dataclass = True
                    break
                if (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Name)
                    and dec.func.id == "dataclass"
                ):
                    is_dataclass = True
                    break
            if is_dataclass:
                dataclasses_.append(node)

            is_enum = False
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "Enum":
                    is_enum = True
                    break
                if isinstance(base, ast.Attribute) and base.attr == "Enum":
                    is_enum = True
                    break

            if is_enum:
                enum_props: list[ast.FunctionDef] = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and has_property_decorator(item):
                        enum_props.append(item)

                if len(enum_props) > best_enum_properties_count:
                    best_enum_properties = enum_props
                    best_enum_properties_count = len(enum_props)

        elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            public_functions.append(node)

        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name_ = node.target.id
            if name_.upper() == name_ and not name_.startswith("_") and node.annotation is not None:
                public_typed_constants.append(node)

    public_functions.sort(key=lambda n: n.name)
    public_typed_constants.sort(key=lambda n: n.target.id)
    best_enum_properties.sort(key=lambda fn: fn.name)

    return ModuleScan(
        dataclasses=dataclasses_,
        public_functions=public_functions,
        public_typed_constants=public_typed_constants,
        enum_properties=best_enum_properties,
    )
