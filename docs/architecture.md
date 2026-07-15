# Architecture

TCalc splits into a **native C++ core** and a **Python orchestration + UI layer**,
bridged by pybind11 as the `calc_native` module.

The native core owns everything hot, precise, or type-heavy: tokenizing the input
string, the whole evaluator (the assignment peel, `normalize`, `shunting_yard`, and the
RPN walk), the math kernels, the numeric value types (exact `Rational`, `BigReal`,
`Complex`, `BigComplex`), the `Collection` type, the variable store, and the declarative
**ops table** that both the tokenizer and the evaluator read from. An expression crosses
the boundary once: Python hands a `TokensBranch` to `evaluate()` and gets a value back.

The Python layer owns presentation and orchestration: it drives the PySide6 UI, builds
the render tree from the same tokens, and maps native exceptions to user-facing error
kinds. It does not compute anything itself.

In short: C++ is the deterministic engine, Python is the UI and orchestration layer that
is cheap to iterate on.

## Data flow

A keystroke becomes a result by tokenizing once, then running two paths off the same
`TokensBranch`:

- **Eval path** (`evaluate()`, entirely in C++) produces the computed value shown in the
  result line. It peels off an assignment if the row is one, then `shunting_yard`
  reorders the flat top-level token list from infix into a flat RPN list; the
  operand-carrying tokens (`Latex`, `Paren`, `Call`) are pushed atomically and are *not*
  descended into, so their inner token vectors stay infix. The RPN walk then scans that
  flat list left to right against an operand stack: scalar operands push, operators pop
  their operands and push the result. When the scan hits an atomic operand whose inner
  tokens are still infix (a fraction's numerator, a paren's elements), it recurses,
  shunting and walking that sub-list. `apply()` runs each operation: it homogenizes the
  operand types across the promotion ladder, dispatches to the kernel, and promotes the
  result on overflow or into the complex domain.
- **UI render path** turns the same tokens into the on-screen widget tree of the
  expression editor. When a LaTeX construct is present, `build_math_nodes` (via
  `structural_split`) produces a `MathNode` tree, and `_render_row` turns each node
  into a nested widget (`FractionWidget`, `ParenWidget`, ...) with its own `QLineEdit`
  slots. Plain text and bare parentheses take lighter incremental paths (alias
  normalization, a `ParenWidget`) and never build a structural tree. Qt lays the
  widgets out; there is no custom measure/paint step in the live editor. So the full
  widget tree is interesting only in the LaTeX example below.

The three diagrams trace both paths for the three shapes an expression can take. They
share the same spine (tokenize once, fan out); the differences are where the
interesting work happens.

`tokenize` and `build_math_nodes` are themselves multi-arm, recursive passes; their
internals (the token model, the classification arms, and the render-tree builder) live
in [parser.md](./parser.md). Below they appear as single steps.

### 1. Basic arithmetic: `2 + 5 * (3/4)`

A linear RPN walk, all in C++. A plain `( )` group holding a single element (arity-1: no
top-level comma) is just grouping: it evaluates recursively but returns a scalar, not
a collection.

```mermaid
flowchart TD
    IN(["user types: 2 + 5 * (3/4)"])
    IN -->|"tokenize() [C++]"| TB["TokensBranch{<br/>tokens: [Number(2), Op(+), Number(5), Op(*),<br/>Paren(kind: Paren, elements: tokens[Number(3), Op(/), Number(4)])],<br/>latex_indices: [], paren_indices: [4],<br/>has_latex_descendant: false, has_call: false }"]

    subgraph EVAL ["Eval path &rarr; result line"]
        direction TB
        SY["shunting_yard [C++]<br/>reorder infix to postfix by precedence<br/>flat RPN list: Number(2), Number(5), Paren, Op(*), Op(+)"]
        RUN["eval_rpn [C++]<br/>scan the flat list left to right<br/>operands push to a stack, operators pop and push"]
        SUB["nested operand still infix:<br/>shunt + walk tokens[3, /, 4]"]
        MUL["apply(Mul, [5, 3/4])"]
        ADD["apply(Add, [2, 15/4])"]
        KERN["arithmetic kernel [C++]"]
        SY -->|flat RPN list| RUN
        RUN -->|"ParenToken operand: recurse"| SUB
        SUB -->|"Rational(3,4)"| MUL
        RUN -->|"Op(*): pop 5 and 3/4"| MUL
        RUN -->|"Op(+): pop 2 and 15/4"| ADD
        MUL -->|"15/4"| ADD
        MUL -.->|"coerce + kernel dispatch"| KERN
        ADD -.-> KERN
    end

    subgraph REND ["UI render path &rarr; expression display"]
        direction TB
        ED["Editor [UI]<br/>QLineEdit segment in an ExpressionSlot"]
        GATE{"has LaTeX descendant?"}
        NORM["normalize_text [UI]<br/>rewrite operator aliases as symbols (flat text)"]
        PW["RoundParenWidget [UI]<br/>incremental ( ) path"]
        INNER["inner ExpressionSlot<br/>holds '3/4'"]
        ED --> GATE
        GATE -->|"no, plain run"| NORM
        GATE -->|"no, ( ) typed"| PW
        PW --> INNER
    end

    TB --> SY
    TB --> ED
    KERN -->|"Rational(23,4)"| RES(["result line: 23/4 = 5.75"])
    NORM --> DISP(["display: 2 + 5 &middot; (3/4)"])
    INNER --> DISP

    classDef input fill:#455a64,stroke:#263238,color:#fff;
    classDef cpp fill:#1565c0,stroke:#0d47a1,color:#fff;
    classDef py fill:#f9a825,stroke:#f57f17,color:#000;
    classDef ui fill:#00838f,stroke:#004d40,color:#fff;
    classDef out fill:#2e7d32,stroke:#1b5e20,color:#fff;
    class IN input;
    class TB,SY,KERN,RUN,SUB,MUL,ADD cpp;
    class ED,GATE,NORM,PW,INNER ui;
    class RES,DISP out;

    linkStyle 0,1,2,3,4,5,6,7,8,13 stroke:#1565c0,stroke-width:2px;
    linkStyle 9,10,11,12,14 stroke:#00838f,stroke-width:2px;
    linkStyle 15,16,17 stroke:#2e7d32,stroke-width:2px;
```

### 2. LaTeX expression: `1 + \frac{1+2}{4}`

A LaTeX token is an atomic operand in the RPN stream. Its `left` and `right`
sub-rows are independently shunting-yard'd and evaluated, then the token's own op is
applied.

```mermaid
flowchart TD
    IN(["user types: 1 + \frac{1+2}{4}"])
    IN -->|"tokenize() [C++]"| TB["TokensBranch{<br/>tokens: [Number(1), Op(+),<br/>Latex(kind: Frac, op_id: Div,<br/>left: tokens[Number(1), Op(+), Number(2)],<br/>right: tokens[Number(4)])],<br/>latex_indices: [2], paren_indices: [],<br/>has_latex_descendant: false, has_call: false }"]

    subgraph EVAL ["Eval path &rarr; result line"]
        direction TB
        SY["shunting_yard [C++]<br/>flat RPN list: Number(1), Latex(Frac), Op(+)<br/>Latex is atomic, not descended into"]
        RUN["eval_rpn [C++]<br/>scan the flat list left to right, operand stack"]
        LE["left still infix:<br/>shunt + walk tokens[1, +, 2]"]
        RE["right still infix:<br/>shunt + walk tokens[4]"]
        FR["apply(Div, [3, 4]) for the Frac op"]
        ADD["apply(Add, [1, 3/4])"]
        KERN["arithmetic kernel [C++]"]
        SY -->|flat RPN list| RUN
        RUN -->|"LatexToken operand: recurse sub-rows"| LE
        RUN -->|"LatexToken operand: recurse sub-rows"| RE
        LE -->|"3"| FR
        RE -->|"4"| FR
        RUN -->|"Op(+): pop 1 and 3/4"| ADD
        FR -->|"Rational(3,4)"| ADD
        ADD -.->|"coerce + kernel dispatch"| KERN
    end

    subgraph REND ["UI render path &rarr; expression display"]
        direction TB
        ED["Editor [UI]<br/>QLineEdit segment, has LaTeX"]
        BMN["build_math_nodes [C++]<br/>structural_split carves the LaTeX out"]
        RR{"_render_row [UI]<br/>walk MathNodes, dispatch per MathNodeKind"}
        TXT["QLineEdit segment<br/>text '1 + '"]
        FW["FractionWidget [UI]"]
        NUM["numerator ExpressionSlot"]
        DEN["denominator ExpressionSlot"]
        ED -->|render_node| BMN
        BMN -->|MathNode list| RR
        RR -->|"TextNode '1 + '"| TXT
        RR -->|"LatexNode(Frac)"| FW
        FW -->|left nodes| NUM
        FW -->|right nodes| DEN
    end

    TB --> SY
    TB --> ED
    KERN -->|"Rational(7,4)"| RES(["result line: 7/4"])
    TXT --> DISP(["display: 1 + fraction (1+2 over 4)<br/>Qt lays out the nested slots"])
    FW --> DISP

    classDef input fill:#455a64,stroke:#263238,color:#fff;
    classDef cpp fill:#1565c0,stroke:#0d47a1,color:#fff;
    classDef py fill:#f9a825,stroke:#f57f17,color:#000;
    classDef ui fill:#00838f,stroke:#004d40,color:#fff;
    classDef out fill:#2e7d32,stroke:#1b5e20,color:#fff;
    class IN input;
    class TB,SY,KERN,BMN,RUN,LE,RE,FR,ADD cpp;
    class ED,RR,TXT,FW,NUM,DEN ui;
    class RES,DISP out;

    linkStyle 0,1,2,3,4,5,6,7,8,9,15 stroke:#1565c0,stroke-width:2px;
    linkStyle 10,11,12,13,14,16 stroke:#00838f,stroke-width:2px;
    linkStyle 17,18,19 stroke:#2e7d32,stroke-width:2px;
```

### 3. Collection: `mean[1, 2, 3]`

A `[ ]` (or `( )` point) is built into a native `Collection`, with validation, before any
op touches it. The same path serves the function-call form `mean(1, 2, 3)` (a `Call`
token) and reducers like `min` / `gcd`.

```mermaid
flowchart TD
    IN(["user types: mean[1, 2, 3]"])
    IN -->|"tokenize() [C++]"| TB["TokensBranch{<br/>tokens: [Op(Mean),<br/>Paren(kind: Bracket, elements: [Number(1), Number(2), Number(3)])],<br/>latex_indices: [], paren_indices: [1],<br/>has_latex_descendant: false, has_call: false }"]

    subgraph EVAL ["Eval path &rarr; result line"]
        direction TB
        SY["shunting_yard [C++]<br/>flat RPN list: Paren, Op(Mean)<br/>Paren is atomic operand"]
        RUN["eval_rpn [C++]<br/>scan the flat list left to right, operand stack"]
        B1["each element still infix:<br/>eval per element (shunt + walk)"]
        B2{"validate items<br/>all scalars or all points? nested list?"}
        B3["build Collection.List[1, 2, 3]"]
        ERR(["raise Invalid:<br/>LIST_MIX / LIST_OF_LIST"])
        RED["apply(Mean, [collection])"]
        KERN["statistic kernel [C++]<br/>reduces the collection items"]
        SY -->|flat RPN list| RUN
        RUN -->|"ParenToken operand: recurse"| B1
        B1 --> B2
        B2 -->|"uniform, no nesting"| B3
        B2 -->|"mixed scalars+points, or nested list"| ERR
        RUN -->|"Op Mean: pop collection"| RED
        B3 -.->|"collection operand"| RED
        RED -.->|"kernel dispatch"| KERN
    end

    subgraph REND ["UI render path &rarr; expression display"]
        direction TB
        ED["Editor [UI]<br/>QLineEdit segment in an ExpressionSlot"]
        GATE{"has LaTeX descendant?"}
        NORM["normalize_text [UI]<br/>'mean' run kept as flat text"]
        BW["BracketWidget [UI]<br/>incremental [ ] path"]
        INNER["inner ExpressionSlot<br/>holds '1, 2, 3'"]
        ED --> GATE
        GATE -->|"no, plain run"| NORM
        GATE -->|"no, [ ] typed"| BW
        BW --> INNER
    end

    TB --> SY
    TB --> ED
    KERN -->|"2.0"| RES(["result line: 2.0"])
    NORM --> DISP(["display: mean[1, 2, 3]"])
    INNER --> DISP

    classDef input fill:#455a64,stroke:#263238,color:#fff;
    classDef cpp fill:#1565c0,stroke:#0d47a1,color:#fff;
    classDef py fill:#f9a825,stroke:#f57f17,color:#000;
    classDef ui fill:#00838f,stroke:#004d40,color:#fff;
    classDef out fill:#2e7d32,stroke:#1b5e20,color:#fff;
    classDef err fill:#c62828,stroke:#8e0000,color:#fff;
    class IN input;
    class TB,SY,KERN,RUN,B1,B2,B3,RED cpp;
    class ED,GATE,NORM,BW,INNER ui;
    class RES,DISP out;
    class ERR err;

    linkStyle 0,1,2,3,4,6,7,8,13 stroke:#1565c0,stroke-width:2px;
    linkStyle 5 stroke:#c62828,stroke-width:2px;
    linkStyle 9,10,11,12,14 stroke:#00838f,stroke-width:2px;
    linkStyle 15,16,17 stroke:#2e7d32,stroke-width:2px;
```

Collection building raises a few more validation errors that this example does not
hit, all from the collection arm of the evaluator: a point `( )` rejects a nested collection item
(`POINT_ITEM_COLLECTION`) and an empty `()` (`EMPTY_POINT`), and a `{ }` brace is not a
collection (`BRACE_UNSUPPORTED`). The call path adds arity checks: a fixed-arity call
with the wrong count (`takes_arguments`), a scalar function handed a collection
(`not_for_list_or_point`), and a call-only function typed bare without parentheses
(`needs_call_form`).

## Native layer (C++)

Under `src/native/`:

- `lib/calc/` math kernels (`arithmetic`, `trig`, `transcendental`, `combinatorics`,
  `number_theory`, `statistic`) behind the `Calculator` facade (`pub/calculator.hpp`).
  Errors are raised as `CalculatorError` with messages centralized in
  `pub/error_messages.hpp` (`tcalc::errmsg`).
- `lib/parser/` the token model and parsing (`pub/parser.hpp`): `tokenize`, the
  structural render-tree builder (`build_math_nodes`, `structural_split`), and the
  **ops table** (`pub/ops.hpp`). Internals in [parser.md](./parser.md).
- `lib/eval/` the evaluator (`pub/eval.hpp`): `evaluate` (assignment peel plus the walk),
  `normalize`, `shunting_yard`, `eval_rpn`, `apply` (the promotion ladder and kernel
  dispatch), `literal_value`, and the native variable store (`VarStore`).
- `lib/collection/` the immutable `Collection` (List / Point), stored as an array of
  typed-variant items (`CollectionItem`). (A columnar SoA representation is drafted but
  not yet implemented.)
- `lib/types.hpp` the numeric value types: exact `Rational` (`boost::rational`),
  `BigReal` (`cpp_dec_float_50`), `Complex`, `BigComplex`.
- `python/bindings/` pybind11 bindings (one file per type), assembled in
  `module.cpp` into the `calc_native` module.

## Python layer

Under `src/tcalc/`:

- `core/native_eval.py` the thin entry to the native evaluator: `evaluate_branch` calls
  `calc_native.evaluate` and maps a native `CalculatorError` (and its `ErrorKind`) to the
  Python error kind. It computes nothing itself.
- `core/parser.py` the `tokenize` and `tokenize_string` wrappers over `calc_native`. The
  render tree is built from the tokens they return.
- `core/ops.py` the Python mirror of the ops table, built at import time from
  `calc_native.op_table()`. There is no second source of truth. Because the
  `Operation` enum and friends are assembled dynamically at runtime, a type checker
  cannot see their members; `scripts/stubgen/generate_ops_stub.py` parses this module's
  AST and reconstructs them into a static `stubs/tcalc/core/ops.pyi`.
- `errors.py` `ErrorKind` plus the `Msg` tables for user-facing error text.
- `ui/` the PySide6 layer. `controller/` drives the loop (tokenize, live preview,
  status); `widgets/math/` renders the LaTeX-style nodes from `build_math_nodes`;
  `widgets/calc/display/` holds the expression editor and result.

## Key design decisions

- **The ops table is the single source of truth.** Each operation is one declarative
  `OpSpec` row (symbol, precedence, associativity, arity, aliases, native method name,
  call arity) defined once in C++. The tokenizer, the shunting-yard, and the evaluator
  all read the same table. Adding an op is a table entry plus a kernel function, not a
  new class in two languages.

- **The evaluator is native; Python is UI and orchestration.** An expression crosses the
  boundary once (`evaluate(branch)`), not once per operation. Everything deterministic
  or type-heavy (tokenizing, the RPN walk, arithmetic, type promotion, collection
  validation, error text, the variable store) lives in C++. Python drives the UI, builds
  the render tree, and maps native errors to user-facing kinds.

- **`Paren` and `Call` are distinct token kinds.** A function call carries an op id and
  multiple arguments; a paren carries grouping or collection elements. Keeping them
  separate lets `mean(1,2,3)` and `mean[1,2,3]` share collection-building while a call
  still knows its arity and rejects bare-infix forms.

- **Exact first, promote on demand.** Integers and fractions stay exact `Rational`s as
  long as possible. Values promote up the ladder (`Rational` -> `BigReal` /
  `Complex` -> `BigComplex`) only when an op needs it. Which arms an op supports is
  derived from the `Calculator` method signatures themselves, not from a hand-kept flag
  table, so it cannot drift.

- **All type stubs are generated, none hand-written.** Two generators feed `stubs/`,
  and `make stub-gen` runs both. The native module is a compiled extension with no
  Python source, so `pybind11-stubgen` introspects `calc_native` into
  `stubs/calc_native.pyi` (then a small `sed` patch fixes self-referential type names).
  The Python side builds its `Operation` enum and other tables dynamically at runtime,
  invisible to a type checker, so an AST-based generator (`scripts/stubgen/`)
  reconstructs them into static `.pyi` files. Keeping no stub by hand means the typed
  surface never drifts from the C++ table or the runtime-built tables: regenerate and
  it is correct by construction.
