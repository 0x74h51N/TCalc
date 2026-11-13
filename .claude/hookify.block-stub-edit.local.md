---
name: block-stub-edit
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: (^|/)stubs/
---

**Editing a generated stub.** Every file under `stubs/` is generated: `calc_native.pyi` by `pybind11-stubgen`, the `tcalc` stubs by `scripts/stubgen/`. Fix the binding or the generator and run `make stub-gen`. See `docs/rules/ai/code.md`.
