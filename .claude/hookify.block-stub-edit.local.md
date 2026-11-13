---
name: block-stub-edit
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: (^|/)stubs/|\.pyi$
---

**Editing a generated stub.** Every `.pyi` is generated: `stubs/calc_native.pyi` by `pybind11-stubgen`, `src/tcalc/core/ops.pyi` by `scripts/stubgen/`. Fix the binding or the generator and run `make stub-gen`. See `docs/rules/ai/code.md`.
