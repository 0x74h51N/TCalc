from __future__ import annotations

from pathlib import Path

from setuptools import setup

try:
    from pybind11 import get_cmake_dir  # noqa: F401
    from pybind11.setup_helpers import Pybind11Extension, build_ext
except ModuleNotFoundError as exc:
    raise SystemExit(
        "pybind11 is not installed. Activate your venv and run "
        "`pip install pybind11` before building the native module."
    ) from exc

ROOT = Path(__file__).resolve().parent

ext_modules = [
    Pybind11Extension(
        "calc_native",
        [
            str(ROOT / "bindings.cpp"),
            str(ROOT / "calculator.cpp"),
        ],
        include_dirs=[str(ROOT)],
        cxx_std=17,
    )
]

setup(
    name="calc-native",
    version="0.1.0",
    description="Calculator core",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)

