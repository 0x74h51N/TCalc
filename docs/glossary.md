# Glossary

The words used in TCalc's code, docs, issues and reviews, in alphabetical order, each in a sentence or two. Where a term has a deeper doc, the entry links to it.

$\color{#3b82f6}\textbf{Adopt}$: Splicing segments onto the end of a slot (adopt_segments). A ParenWidget adopts the segments that move inside it when a paren is opened or its close glyph is removed.

$\color{#3b82f6}\textbf{Anchor}$: The middle line a slot lines its segments up on. The segment that reaches highest above its own middle sets it; the others get a top margin to meet it.

$\color{#3b82f6}\textbf{Apply}$: Runs one operation in the evaluator (apply in eval.cpp): promotes the operands, calls the kernel, retries in double when an exact result cannot be represented, and promotes the result when it overflows.

$\color{#3b82f6}\textbf{Arithmetic}$: The kernel file of the basic operations (arithmetic.cpp): add, subtract, multiply, divide, power, roots, mod, integer division, floor, ceil and trunc, on every arm.

$\color{#3b82f6}\textbf{Arm}$: One alternative of a Value, named by the Arm enum: Int64, Double, Cx, Big, BigCx, Rat and Coll.

$\color{#3b82f6}\textbf{Assignment}$: A row that stores a value under a single letter, such as A = 2 + 3. The evaluator peels the name off before it evaluates the rest and writes the value into the VarStore.

$\color{#3b82f6}\textbf{Aux slot}$: A slot of a Math Widget that is not a script slot: a numerator, a denominator, a base, a radicand, an inner slot. The theme styles aux and script slots by their kind.

$\color{#3b82f6}\textbf{Bencho}$: A benchmark test (tests/benchmark, make py-benchmark). Also a great samurai swordsman from Japan: legend says he drew his katana, took his enemy's head and sheathed it again in 200 ms. TCalc considers Bencho threshold before the Doherty threshold.

$\color{#3b82f6}\textbf{Bernoulli numbers}$: Rational sequence giving the coefficients of Faulhaber's formula. Jacob Bernoulli (1713). Tabulated B₀ to B₂₄, with B₁ = +1/2.

$\color{#3b82f6}\textbf{Bessel's correction}$: Division by n − 1 instead of n in the sample variance, for an unbiased estimate. Friedrich Bessel.

```math
s^{2} = \frac{1}{n-1}\sum_{i=1}^{n}(x_i - \bar{x})^{2}
```

$\color{#3b82f6}\textbf{Big}$: The arm of a Value that holds a BigReal.

$\color{#3b82f6}\textbf{BigComplex}$: A complex number on two 50-digit decimals, Boost's cpp_complex_50.

$\color{#3b82f6}\textbf{BigCx}$: The arm of a Value that holds a BigComplex.

$\color{#3b82f6}\textbf{BigReal}$: A 50-digit decimal with a wide exponent range, Boost's cpp_dec_float, for results a double cannot hold or keep exact enough.

$\color{#3b82f6}\textbf{Binary exponentiation}$: Integer power by repeated squaring, about log₂ n multiplications for the exponent n. Used by the closed forms for exact and BigReal powers.

$\color{#3b82f6}\textbf{Binding layer}$: The pybind11 code that exposes the native core to Python as calc_native (src/native/python/), one file per type under bindings/, assembled in module.cpp.

$\color{#3b82f6}\textbf{Boost}$: The super sexy high-precision C++ math library. TCalc's precision engine. Multiprecision gives BigReal, BigComplex and the big integers of the closed forms, Rational gives Rational, Math gives the constants and the BigReal gamma function. ([src](https://github.com/boostorg/boost))

$\color{#3b82f6}\textbf{Bottom slot}$: Of a Math Widget with two slots, the one drawn lower. Down moves the cursor from the top slot into it. It follows the drawing, not the LaTeX text, so it can be the left slot or the right slot.

$\color{#3b82f6}\textbf{Braces}$: Curly brackets in an expression. They only group: a comma inside braces is an error, so braces never make a Collection.

$\color{#3b82f6}\textbf{Brute force}$: Evaluating an iterated op by looping over its whole range, the fallback when no closed form fits the body. The deadline stops a loop that runs too long.

$\color{#3b82f6}\textbf{Calculator}$: The native class (calc/pub/calculator.hpp) that holds every kernel as a method. The ops table names one method per op, and the arms an op accepts come from that method's overloads.

$\color{#3b82f6}\textbf{CalculatorError}$: The native error. It carries an error kind and a message from the native message table (errmsg); the Python side maps it to its own error kind.

$`\color{#3b82f6}\textbf{calc\_native}`$: The Python module of the native core, built by the binding layer: tokenize, evaluate, the ops and constant tables, the value types. Its stub (stubs/calc_native.pyi) is generated. Unit tests use a fake of it.

$\color{#3b82f6}\textbf{CallToken}$: A function call with its arguments, an OpId and the argument list.

$\color{#3b82f6}\textbf{Cascade}$: After a dissolve, a ParenWidget around the cursor that no longer holds a Math Widget dissolves too.

$\color{#3b82f6}\textbf{CharToken}$: A single ASCII letter, a one-letter variable. Letters side by side become an implicit product.

$\color{#3b82f6}\textbf{Closed form}$: Answering an iterated op in one step from the shape of its body instead of looping over the range (closed_forms.cpp): polynomial sums by Faulhaber's formula, geometric sums, periodic trig sums, products with no bound variable. A body no closed form fits goes to brute force.

```math
\sum_{n=1}^{m} n = \frac{m(m+1)}{2}
```

$\color{#3b82f6}\textbf{Coll}$: The arm of a Value that holds a Collection.

$\color{#3b82f6}\textbf{Collection}$: An immutable sequence of values, a List or a Point (CollectionKind). Its items are scalars or Points, and on construction they are promoted to one common arm. Copying a Collection shares its items instead of copying them.

$\color{#3b82f6}\textbf{Combinatorics}$: The kernel file of counting (combinatorics.cpp): factorial, gamma, permutations (nPr) and combinations (nCr).

```math
\bar{x}\left[10^{16}, 1, -10^{16}\right] = \frac{1}{3}
```

$\color{#3b82f6}\textbf{Compensated summation}$: Summation that tracks the rounding error of each addition and adds it back. Used by sum, mean and variance on the Double and Complex arms; error about two machine epsilons, independent of count and magnitude spread.

$\color{#3b82f6}\textbf{Complex}$: A complex number on two doubles.

$\color{#3b82f6}\textbf{ConstToken}$: A named constant such as π, e or a physical constant, known by its ConstId.

$\color{#3b82f6}\textbf{Correctly rounded}$: The exact value rounded to the nearest number of the type. The complex root test rows expect it: the exact root computed at 400 bits, rounded to double or to the BigComplex.

$\color{#3b82f6}\textbf{Cx}$: The arm of a Value that holds a Complex.

$\color{#3b82f6}\textbf{Çiçek}$: 1. Everything's coming up roses. 2. All systems are operational.

$\color{#3b82f6}\textbf{Deadline}$: The wall-clock budget of one evaluation, 500 ms in the app. It starts at the outermost evaluate, and long loops check it and stop with an error, so a heavy expression cannot freeze the app.

$\color{#3b82f6}\textbf{Debug tree dump}$: What python -m tcalc --debug logs each time the editor's plain text changes: the math nodes of the text (MATH_NODES), then the TreeInfo of the editor under the header Expression Tree. A failing case of test_expression.py prints the same tree.

$\color{#3b82f6}\textbf{Detach}$: Taking the segments after one segment out of a slot without deleting them (detach_right_of), so they can be adopted somewhere else.

$\color{#3b82f6}\textbf{Dirichlet form}$: Product form of a sum of sines or cosines over an arithmetic progression of angles; the Dirichlet kernel identity, Peter Gustav Lejeune Dirichlet. Closes trig sums whose angle is not a rational multiple of a half turn.

$\color{#3b82f6}\textbf{Dissolve}$: Removing a Math Widget and keeping the content of its slots in its place, as when Backspace removes a fraction bar.

$\color{#3b82f6}\textbf{Domain rule}$: The part of an op's row that says when a real operand leaves the op's real domain, so it is widened to complex before the kernel runs: sqrt of a negative, log of a non-positive (DomainRule). It is written once and read in the operands' own type.

$\color{#3b82f6}\textbf{Double}$: The arm of a Value that holds a double, a 64-bit floating-point number.

$\color{#3b82f6}\textbf{Downcast}$: The opposite of promotion: a Rational moved down to Int64 when it is a whole number and to Double otherwise (rational_downcast). It happens in coerce, for an op with no exact arm, and in the retry after an exact kernel fails, as for an irrational root. A BigReal is never downcast.

$\color{#3b82f6}\textbf{Edge}$: The raised look of a key, a panel or a widget in a theme (Edge in look.py): a border of a set width with a light color on one side and a shadow color on the other. A width of 0 turns it off.

$\color{#3b82f6}\textbf{Editor}$: The math-mode input, Expression in expression.py. It holds the main slot, routes each key to a field, and handles Backspace, the arrow keys, negate, LaTeX expressions and parens. When a field changes it asks the renderer to rebuild that field and emits the whole row as plain text for the live result. Its layout rules and dissolve paths are in [editor.md](editor.md).

$\color{#3b82f6}\textbf{Error kind}$: The class of an error the user sees: Invalid, Malformed or Math Error. The native ErrorKind and the Python ErrorKind mirror each other.

$\color{#3b82f6}\textbf{Eval}$: The path of a row that computes its result, next to the render path that draws it. It starts from the same TokensBranch the editor renders, runs entirely in the native evaluator, and ends in a Value for the result line. Specs, tests and commits use the word for this step (eval layer, eval tests, the eval scope of a commit).

$\color{#3b82f6}\textbf{Evaluator}$: The native layer that computes a row (lib/eval): it peels an assignment, normalizes the tokens, orders them with the shunting-yard, walks the RPN and applies each operation. Python calls it once per row (evaluate).

$\color{#3b82f6}\textbf{Exact integer sum}$: On the Int64 arm, sum and mean add into a 128-bit integer, so the total cannot overflow before the division.

$\color{#3b82f6}\textbf{Exact rule}$: A rule of one op that runs before its kernel and answers an exact value the kernel could not (exact.cpp), from the tokens before evaluation or from an exact table. It declines when it has no answer, and the kernel runs as usual. Sin, cos, tan, exp, pow, ln and log have one.

```math
\sin(\pi) = 0 \qquad \sin(30^\circ) = \tfrac{1}{2}
```

$\color{#3b82f6}\textbf{Expression}$: What the user types in one row, plain text with LaTeX expressions inside. In math mode the editor shows it as Math Widgets.

$\color{#3b82f6}\textbf{ExpressionNode}$: The base class of every Math Widget (renderer/expression_node.py). It holds a left slot and, by its kind, a right, a top and a bottom slot, and names its op, its LatexKind and its symbol as class constants. It writes itself back as LaTeX text through format_expr_str, or as its left slot's text when it has no symbol, as a paren does; it puts the cursor in its right slot when it is made, or in its left slot when it has no right one, tells Up and Down which slot lies above or below, and dissolves into the slot around it.

$\color{#3b82f6}\textbf{ExpressionSlot}$: The Qt widget behind every slot (renderer/expression_node.py). It lays out its segments in a row, creates its fields, and gives the editor and the renderer the operations that change the row: insert a Math Widget, splice segments in and merge the fields that meet, remove one. It writes its row back as plain text and keeps its segments on one anchor through the margin update. Each one is a main slot, an aux slot or a script slot.

$\color{#3b82f6}\textbf{Faulhaber's formula}$: Closed form of a sum of powers as a polynomial in the upper bound, coefficients from the Bernoulli numbers. Johann Faulhaber (1631). Used for polynomial sums up to degree 24.

```math
\sum_{n=1}^{m} n^{2} = \frac{m(m+1)(2m+1)}{6}
```

$\color{#3b82f6}\textbf{Field}$: A text input of a slot, where the user types: an ExprInput, which is a QLineEdit. It is named after its slot and its index, as main_0 or numerator_0.

$\color{#3b82f6}\textbf{First index}$: Of a field, index 0. Of a slot, index 0 of its first field.

$\color{#3b82f6}\textbf{Flower}$: Çiçek.

$\color{#3b82f6}\textbf{Fold}$: Another word for a reduction: walking the items and combining them into one value.

$\color{#3b82f6}\textbf{Frac}$: The LatexKind of a fraction: the numerator left, the denominator right. It evaluates through OpId::Div.

$\color{#3b82f6}\textbf{Gamma function}$: Extension of the factorial to non-integers: Γ(n + 1) = n!. Leonhard Euler (1729). Computes factorials of non-integers and the gamma op.

$\color{#3b82f6}\textbf{Gaussian integer}$: A complex number whose real and imaginary parts are both integers, such as 3 + 4i. The root of one is often one too: (-117 + 44i) at degree 3 is 3 + 4i.

$\color{#3b82f6}\textbf{Geometric sum}$: Sum with a constant ratio r between terms, closed by the formula below. Closed for affine exponents and like terms. A ratio of 1 never reaches the formula: the term folds to a constant, and the sum is m + 1 times it.

```math
\sum_{n=0}^{m} r^{n} = \frac{r^{m+1}-1}{r-1}
```

$\color{#3b82f6}\textbf{Glyph}$: A symbol drawn as a path rather than typed, a MathPrimitive (math_primitives.py): the radical sign of a root (SqrtSymbol) and the paren glyphs (RoundParen, SquareBracket, CurlyBrace). It is rebuilt at the widget's size, so it stretches with what it encloses.

$\color{#3b82f6}\textbf{Guard digits}$: The digits a BigReal keeps past the 50 it promises. Boost does its arithmetic in them, so an exact result can sit just off its value there: 9e400/3e400 is 3 at 50 digits and a hair under 3 in the guard digits.

$\color{#3b82f6}\textbf{Half turn}$: An angle as a multiple of π, the unit the exact trig table works in: 30° is 1/6 of a half turn.

$\color{#3b82f6}\textbf{Index}$: A cursor position in a field, counted in characters: 0 is before the first character, the text length is after the last.

$\color{#3b82f6}\textbf{Inner slot}$: The one slot of a ParenWidget, between its paren glyphs, which are segments of it. It starts with the open glyph instead of a field, and its plain text includes the paren symbols.

$\color{#3b82f6}\textbf{Int64}$: The arm of a Value that holds a 64-bit integer.

$\color{#3b82f6}\textbf{Integer fold}$: Pairwise left fold of gcd or lcm over a List of integers (fold_integers in number_theory.cpp).

$\color{#3b82f6}\textbf{Iterated op}$: A sum (Σ) or product (Π) of a body over a bound variable and a range. It is evaluated by a closed form when one fits, else by brute force.

```math
\sum_{n=1}^{10} n^{2} \qquad \prod_{k=1}^{5} k
```

$\color{#3b82f6}\textbf{Kahan summation}$: Compensated summation, William Kahan (1965). Loses the correction when an item exceeds the running sum.

$\color{#3b82f6}\textbf{Kernel}$: The math function that computes one op on one arm, a method of the Calculator. The kernel files group them: arithmetic, combinatorics, number theory, statistic, transcendental, trig.

$\color{#3b82f6}\textbf{Last index}$: Of a field, the index after its last character. Of a slot, the last index of its own last field, never of a field inside a Math Widget it holds.

$\color{#3b82f6}\textbf{LaTeX expression}$: One LaTeX construct TCalc understands, with its slots in braces or brackets: fraction, power, subscript, sqrt, sum and product. Each has its LatexKind and its symbol. The table comes from the native module, and Python mirrors it as LatexExpr.

```math
\frac{a}{b} \qquad x^{n} \qquad x_{n} \qquad \sqrt[n]{x} \qquad \sum_{i=1}^{n} \qquad \prod_{i=1}^{n}
```

$\color{#3b82f6}\textbf{LatexKind}$: The kind of a LaTeX expression: Frac, Pow, Subscript, Sqrt, SqrtN, Sum or Prod.

$\color{#3b82f6}\textbf{LatexSplit}$: A structural split around a LatexToken: the prefix, the left side, the right side and the suffix. An empty side is filled by the operand split.

$\color{#3b82f6}\textbf{LatexToken}$: A LaTeX expression: its LatexKind, its OpId, and the tokens of its left and right slots.

$\color{#3b82f6}\textbf{Left}$: 1. The LatexToken field that holds the first operand of its op: the numerator, the base, the radicand, the lower limit. 2. The math node field built from it, the row the left slot renders. 3. The correct political stance of this application.

$\color{#3b82f6}\textbf{Left slot}$: The slot of a Math Widget that renders its left side. Every Math Widget has one; a ParenWidget has only this one.

$\color{#3b82f6}\textbf{Like-term folding}$: Adding the coefficients of terms with the same symbolic part: 3 sin(n) + sin(n) is 4 sin(n). Terms are collected by canonical key, so cancelling terms cancel exactly.

$\color{#3b82f6}\textbf{List}$: Written in square brackets. Its items are all scalars or all Points of the same arity; a List inside a List is not allowed.

```math
[1, 2, 3]
```

$\color{#3b82f6}\textbf{List of Points}$: A List whose items are Points of the same arity.

```math
[(1, 2), (3, 4)]
```

$\color{#3b82f6}\textbf{Literal}$: What a number written in the expression means (literal.cpp): an exact integer, an exact Rational for a decimal that fits one, a double, a BigReal when it is out of double's range, or a Complex for an imaginary literal such as 3i.

$\color{#3b82f6}\textbf{Main slot}$: The editor's outermost slot, the one every other slot sits inside. Its fields are named main_0, main_2 and so on. The code, the debug tree dump and the tests call it root.

$\color{#3b82f6}\textbf{Mal}$: Prod, in its first sense.

$\color{#3b82f6}\textbf{Margin update}$: A slot setting its segments on its anchor and stretching its paren glyphs to the full height. It runs after a change or a resize, then asks the slot around it to do the same, up to the main slot. A read-only slot does it once and stays fixed.

$\color{#3b82f6}\textbf{Math node}$: One node of the tree that build_math_nodes builds from the tokens for the editor: text, a paren with its children, or a LaTeX expression with its left and right children. Math nodes are data; Math Widgets draw them. See [parser.md](parser.md#build_math_nodes-render-tree).

$\color{#3b82f6}\textbf{Math Widget}$: The Qt widget of one LaTeX expression or paren in the editor, an ExpressionNode: FractionWidget, PowWidget, SubWidget, SqrtWidget, SqrtNWidget and the ParenWidget kinds RoundParenWidget, BracketWidget and BraceWidget. Sum and product have no Math Widget yet.

$\color{#3b82f6}\textbf{Max}$: A reduction: the largest item of a Collection. Not defined for complex values.

$\color{#3b82f6}\textbf{Mean}$: A reduction: the sum of a Collection's items divided by their count. Symbol x̄, alias mean.

```math
\bar{x} = \frac{1}{n} \sum_{i=1}^{n} x_i
```

$\color{#3b82f6}\textbf{Median}$: A reduction: the middle item of a Collection in sorted order; with an even count, the mean of the two middle items. It is found by selection (nth_element), without sorting the whole List. Not defined for complex values.

$\color{#3b82f6}\textbf{Merge}$: Joining two neighboring fields of a slot into one (\_merge_edits): the right field's text is appended to the left field, and the right field is removed.

$\color{#3b82f6}\textbf{Merge point}$: A place where a splice puts two fields side by side, so they merge. The left merge point is where the field before the spliced segments meets the first of them; the right merge point is where the last of them meets the field after. After a dissolve the cursor lands at the left merge point today, which #184 is about.

$\color{#3b82f6}\textbf{Min}$: A reduction: the smallest item of a Collection. Not defined for complex values.

$\color{#3b82f6}\textbf{Neumaier summation}$: Compensated summation, Arnold Neumaier (1974); also Kahan-Babuška-Neumaier. Correct whichever operand is larger. TCalc's summation (neumaier_sum in statistic.cpp).

$\color{#3b82f6}\textbf{Newton}$: Newton's method, also Newton-Raphson: finds a root of f by repeating z = z - f(z) / f'(z) from a starting guess. The complex root runs it on z^n - x from the pow guess, in a BigComplex, through Boost's complex_newton.

$\color{#3b82f6}\textbf{Niven's theorem}$: At rational multiples of π, the only rational values of sine and cosine are 0, ±1/2 and ±1. Ivan Niven (1956). Basis of the exact trig table: sine and cosine exact at twelfths of a turn, tangent at quarters.

$\color{#3b82f6}\textbf{NodeInfo}$: One Math Widget in a TreeInfo, printed as Node<class name> with its slots under it.

$\color{#3b82f6}\textbf{Noise}$: Floating point noise: a tiny wrong part in a result that is exact in math, left by rounding on an inexact path. Calculator::root took the square root of -4 through exp and log and left 1.2246467991473532e-16 as the real part of 2i. The result formatter hides a part smaller than 1e-12, so noise shows once the value is scaled up.

$\color{#3b82f6}\textbf{Normalize}$: The first step of ordering the tokens: it inserts the implicit multiplications and folds runs of + and - into one sign, so 2π becomes 2 · π and 3 - - 2 becomes 3 + 2.

$\color{#3b82f6}\textbf{Number set}$: The set results are computed in. TCalc computes real first and promotes to complex where the reals have no value; letting the user choose the set is #230.

$\color{#3b82f6}\textbf{Number theory}$: The kernel file of gcd and lcm (number_theory.cpp).

$\color{#3b82f6}\textbf{NumberToken}$: A number, kept as its text until the evaluator reads it.

$\color{#3b82f6}\textbf{Odd root}$: A root of odd degree. It keeps the sign, so a negative number has a real one: the cube root of -8 is -2. A negative number has no real even root.

$\color{#3b82f6}\textbf{Operand split}$: Filling an empty side of a LaTeX expression from its neighbour (split_operand): the last operand of the prefix goes into the left side, the first operand of the suffix into the right side, when that operand is a number, a letter, a constant, a paren or a call. It runs in the math nodes only; eval sees it after the editor writes the row back.

$\color{#3b82f6}\textbf{Ops table}$: The one table of operations (OpSpec rows) that the tokenizer, the evaluator and the Python side all read. An op is known by its OpId.

$\color{#3b82f6}\textbf{OpToken}$: An operator or a function name, known by its OpId.

$\color{#3b82f6}\textbf{Overflow}$: A double result that went past the type's range to infinity. Apply then re-runs the op in BigReal (promote_range in eval.cpp), so 10^{400} stays a number. A complex result is not widened this way.

$\color{#3b82f6}\textbf{Painter}$: MathPainter (painter/math_painter.py) draws an expression without widgets, for the history. It builds a layout tree from the math nodes (rows, text leaves and paint nodes), measures and places it once, and paints it on one PaintCanvas. A long history stays fast because no Qt widget is made per node.

$\color{#3b82f6}\textbf{Paren glyph}$: The drawn open or close bracket of a ParenWidget, a segment of its inner slot.

$\color{#3b82f6}\textbf{ParenSplit}$: A structural split around a paren that holds a LaTeX descendant: the prefix, the paren's elements and the suffix.

$\color{#3b82f6}\textbf{ParenToken}$: A group in round brackets, square brackets or braces (ParenKind). One element is a plain grouping; several elements, split on commas, are a collection. It knows whether its open and close are there.

$\color{#3b82f6}\textbf{Parser}$: The native layer that reads an expression (lib/parser): the tokenizer, the math node builder for the editor, and the ops and constant tables. Python reaches it through core/parser.py.

$\color{#3b82f6}\textbf{Pending paren}$: An open ParenWidget still waiting for its close.

$\color{#3b82f6}\textbf{Per-column reduction}$: On a List of Points the reduction runs on each coordinate separately, and the result is a Point. Each column is promoted to its own arm first.

```math
\bar{x}\big[(1, 2), (3, 6)\big] = (2, 4)
```

$\color{#3b82f6}\textbf{Periodic sum}$: Trig sum whose angle is a rational multiple of a half turn. The terms repeat; one period is summed exactly from the half-turn table.

$\color{#3b82f6}\textbf{Plain text}$: The expression as one string, LaTeX included, which the editor builds by joining its slots (get_plain_text). The controller evaluates it, and the debug tree dump prints it last as [plain_text]. The editor emits it as plain_text_changed.

$\color{#3b82f6}\textbf{Point}$: Two or three scalars in round brackets. A single value in round brackets is a plain grouping, not a Point.

```math
(3, 4) \qquad (1, 2, 3)
```

$\color{#3b82f6}\textbf{Population standard deviation}$: A reduction: the square root of the population variance. Symbol σ, alias stdp.

$\color{#3b82f6}\textbf{Population variance}$: A reduction: the squared distance of each item from the mean, summed and divided by n. Symbol σ², alias varp. Not defined for complex values.

```math
\sigma^2 = \frac{1}{n} \sum_{i=1}^{n} \left(x_i - \bar{x}\right)^2
```

$\color{#3b82f6}\textbf{Pow}$: The LatexKind of a power: the base left, the exponent right. It evaluates through OpId::Pow.

$\color{#3b82f6}\textbf{Prefix}$: The field right before a Math Widget, in the same slot. In the expression below, the prefix of the fraction holds 2 +.

```math
2 + \frac{3}{4} + 5
```

$\color{#3b82f6}\textbf{Principal value}$: The one value a complex power or root takes by convention, exp(b log a) with the principal log: (-8)^{1/3} has it at 1+1.73i. A complex number set gives it everywhere.

$\color{#3b82f6}\textbf{Prod}$: 1. Production: the working version of the app, as users run it. 2. The LatexKind of a product: the lower limit left, the upper limit right; its body is the term after it.

$\color{#3b82f6}\textbf{Promotion}$: An op moves its operands to a common arm before it runs, and a result moves up when it overflows or leaves the real numbers: Rational, then BigReal or Complex, then BigComplex. Which arms an op takes comes from the Calculator method signatures, not from a hand-kept table.

$\color{#3b82f6}\textbf{PySide6}$: Qt's official Python bindings. The PySide6 layer is TCalc's UI (src/tcalc/ui).

$\color{#3b82f6}\textbf{QLineEdit}$: Qt's one-line text input. Every field is one, so the debug tree dump prints a field as QLineEdit(main_0).

$\color{#3b82f6}\textbf{Qt}$: The C++ GUI framework of TCalc's UI, used from Python through PySide6. ([src](https://github.com/qt/qtbase))

$\color{#3b82f6}\textbf{Rat}$: The arm of a Value that holds a Rational.

$\color{#3b82f6}\textbf{Rational}$: An exact fraction of two 64-bit integers, Boost's rational. Integers and fractions stay Rational as long as an op allows, so a result like the one below stays exact.

```math
\frac{1}{3} + \frac{1}{6} = \frac{1}{2}
```

$\color{#3b82f6}\textbf{Real first}$: TCalc's rule for a negative base: an exact exponent p/q with an odd q gives the real value, the q-th root of the p-th power; an even q, or an exponent computed as a double, gives the principal value. A typed decimal is exact too: 0.2 is 1/5, so (-32)^{0.2} is -2, while (-2)^{0.5} is 1.414i.

$\color{#3b82f6}\textbf{Reduction}$: An op that folds a Collection into one value: mean, sum, min, max, median, variance, standard deviation.

$\color{#3b82f6}\textbf{Reduction driver}$: The one function every reduction goes through (reduce_collection in statistic.cpp). It rejects an empty Collection and a single Point, and hands a List of Points to the per-column reduction. Each op only supplies its scalar reducer for each arm.

$\color{#3b82f6}\textbf{Reinventing the wheel}$: Writing again what the standard library, Boost, Qt or TCalc already provides. The rule is to use or extend what exists first (docs/rules/ai/code.md).

$\color{#3b82f6}\textbf{Render mode}$: How an expression is shown: Math with Math Widgets, Flat as one line of text, Raw as the LaTeX source.

$\color{#3b82f6}\textbf{Renderer}$: MathRender (renderer/math_render.py) turns the tokens of one field into Math Widgets, each with its prefix and suffix, and recurses into their slots. The result display uses a read-only renderer, whose fields cannot be focused or edited.

$\color{#3b82f6}\textbf{Replace with}$: Swapping a Math Widget in a slot for a list of segments (replace_with): the Math Widget is taken out, the segments are spliced in its place, and the field returned by the splice gets the focus. A dissolve with a Math Widget in its left slot goes this way.

$\color{#3b82f6}\textbf{Right}$: 1. The LatexToken field that holds the second operand of its op: the denominator, the exponent, the index of a subscript, the degree, the upper limit. 2. The math node field built from it, the row the right slot renders.

$\color{#3b82f6}\textbf{Right slot}$: The slot of a Math Widget that renders its right side. Left and right name the operand order of the op, not the text order or where the slot is drawn: the LaTeX text of SqrtN writes its degree, the right side, first.

$\color{#3b82f6}\textbf{Root}$: 1. The main slot, as Expression.\_root, the debug tree dump and the test paths of test_expression.py name it. 2. OpId::Root, the n-th root op ⌄ that Sqrt and SqrtN evaluate through, by Calculator::root.

$\color{#3b82f6}\textbf{RPN}$: Reverse Polish notation: postfix, operators after their operands. Reversed form of Jan Łukasiewicz's prefix notation (1924). Produced by the shunting-yard, evaluated by the RPN walk.

```math
2 + 3 \cdot 4 \;\to\; 2\;3\;4\;\cdot\;+
```

$\color{#3b82f6}\textbf{RPN walk}$: Stack evaluation of an RPN list (eval_rpn): operands are pushed, an operator pops its operands and pushes its result. Paren and LaTeX operands are evaluated by a nested walk.

$\color{#3b82f6}\textbf{Sample standard deviation}$: A reduction: the square root of the sample variance. Symbol s, alias std.

$\color{#3b82f6}\textbf{Sample variance}$: A reduction: the squared distance of each item from the mean, summed and divided by n − 1. Symbol s², alias var. Needs at least two items. Not defined for complex values.

```math
s^2 = \frac{1}{n-1} \sum_{i=1}^{n} \left(x_i - \bar{x}\right)^2
```

$\color{#3b82f6}\textbf{Scalar}$: The closed forms' symbolic term: a coefficient times a product of symbols with exponents, such as 3π²; the symbols are constants or session variables. It keeps π as π through the walk, so bodies such as π n² close and constants that cancel stay exact.

$\color{#3b82f6}\textbf{Script fold}$: Tokenizer step that turns ^ or \_ and the following brace group into a LatexToken, with the preceding operand as the base (fold_script). A bare ^ gives an empty exponent.

$\color{#3b82f6}\textbf{Script slot}$: The small raised or lowered slot: an exponent, a subscript, a sqrt degree. The deeper it is nested, the smaller the renderer draws it.

$\color{#3b82f6}\textbf{SegInfo}$: One segment in a SlotInfo, printed with its index. An edit is a field, printed as QLineEdit(name) and its text. A node is a Math Widget, printed as -> with its NodeInfo under it. A glyph is a paren glyph, printed by its class name.

$\color{#3b82f6}\textbf{Segment}$: One item of a slot's row: a field, a Math Widget, or, inside an inner slot, a paren glyph. ExpressionSlot and the debug tree dump use the word this way. In the editor and the renderer, a parameter named seg is always a field, often a prefix or a suffix.

$\color{#3b82f6}\textbf{Selection}$: Finding the k-th smallest item without a full sort, linear on average. The median uses nth_element: introselect, David Musser (1997), built on Tony Hoare's quickselect (1961).

$\color{#3b82f6}\textbf{Shunting-yard}$: Infix to RPN conversion by operator precedence (shunting_yard). Edsger W. Dijkstra's algorithm (1961). Paren, call and LaTeX tokens are single operands; their contents are ordered when the RPN walk reaches them.

$\color{#3b82f6}\textbf{Slot}$: One horizontal row of an expression: the main slot, or one row of a Math Widget (a numerator, an exponent, an inner slot). It holds a line of segments: fields (prefixes and suffixes) and Math Widgets, which hold slots of their own. In the expression below the main slot holds 2 +, the fraction and + 5; the fraction holds two more slots, 3 and 4.

```math
2+\frac{3}{4}+5
```

$\color{#3b82f6}\textbf{SlotInfo}$: One slot in a TreeInfo, printed as Slot[key] with the number of its segments, where key is the slot's name (main, numerator, base). An inner slot also shows its paren symbols.

$\color{#3b82f6}\textbf{Snap}$: Short for snap_integer, and its verb, e.g. snapping a root's degree.

$`\color{#3b82f6}\textbf{snap\_integer}`$: Reads a BigReal as the integer it equals at 50 digits, ignoring its guard digits, and leaves it unchanged otherwise. Used where an integer is asked for (trunc, floor, ceil, a root's degree), not on every operation. Never snaps to zero.

$\color{#3b82f6}\textbf{Splice}$: Inserting segments into a slot at an index and merging the fields that meet at the merge points (\_splice). A paren glyph among them is not inserted; its symbol is written into the field before it. It returns the field at the left merge point, or at the right one when only that one merges.

$\color{#3b82f6}\textbf{Sqrt}$: The LatexKind of a square root, with no degree field. The tokenizer writes its degree, 2, into its right side. It evaluates through OpId::Root.

$\color{#3b82f6}\textbf{SqrtN}$: The LatexKind of an n-th root: the radicand left, the degree right, though the LaTeX text writes the degree first. It evaluates through OpId::Root.

$\color{#3b82f6}\textbf{Statistic}$: The kernel file of the reductions (statistic.cpp): mean, sum, min, max, median, variance and standard deviation over a Collection.

$\color{#3b82f6}\textbf{Structural split}$: The step of build_math_nodes that carves the first Math Widget out of a row (structural_split): a LatexSplit or a ParenSplit, with the prefix and the suffix around it. A row with no LaTeX has none and stays text.

$\color{#3b82f6}\textbf{Subscript}$: The LatexKind of a subscript: the base left, the index right. It has no op.

$\color{#3b82f6}\textbf{Suffix}$: The field right after a Math Widget, in the same slot. In the expression below, the suffix of the fraction holds + 5. Between two Math Widgets there is only one field: the suffix of the first is the prefix of the second.

```math
2 + \frac{3}{4} + 5
```

$\color{#3b82f6}\textbf{Sum}$: 1. A reduction: the total of a Collection's items. Symbol Σ, alias sum. 2. The LatexKind of a sum: the lower limit left, the upper limit right; its body is the term after it.

$\color{#3b82f6}\textbf{TCalc}$: A desktop calculator with a native C++ computation core and a PySide6 UI. The name has no expansion; it was born from frustration with KCalc.

$\color{#3b82f6}\textbf{Token}$: One unit of an expression, with its kind, its data and its start and end position in the text.

$\color{#3b82f6}\textbf{Tokenizer}$: The native pass (tokenize) that turns an expression into tokens in one scan. The details are in [parser.md](parser.md#token-model).

$\color{#3b82f6}\textbf{TokensBranch}$: What the tokenizer returns: the row of tokens, and the positions of its top-level LaTeX and paren tokens.

$\color{#3b82f6}\textbf{Top slot}$: Of a Math Widget with two slots, the one drawn higher. Up moves the cursor from the bottom slot into it. It follows the drawing, not the LaTeX text, so it can be the left slot or the right slot.

$\color{#3b82f6}\textbf{Trait}$: An eval-time property of an op that its kernel signature cannot report (Trait in ops.hpp): ExactZero, RootExponent, InverseDegree. Separate from the op flags the tokenizer reads.

$\color{#3b82f6}\textbf{Transcendental}$: The kernel file of exp, ln, log and the roots (transcendental.cpp).

$\color{#3b82f6}\textbf{TreeInfo}$: A snapshot of the editor's whole tree (snapshot_tree): its root SlotInfo, the plain text, and every slot, Math Widget and field in it. The tests read it to check the tree.

$\color{#3b82f6}\textbf{Trig}$: The kernel file of the trigonometric functions (trig.cpp): sin, cos, tan, their inverses and hyperbolic forms, in degrees, radians or grads, with the exact half-turn table.

$\color{#3b82f6}\textbf{Two-pass variance}$: Variance computed as the mean first, then the sum of squared deviations from it. Avoids the cancellation of the one-pass formula. Neumaier summation on the Double arm.

$\color{#3b82f6}\textbf{Ulp}$: Unit in the last place: the gap between a double and the next one. A result one ulp off is wrong only in its last digit.

$\color{#3b82f6}\textbf{Underflow}$: A double result that fell to zero from nonzero operands, or into the subnormal band below 1e-308, where it sheds digits. Apply re-runs the op in BigReal for it, as for an overflow, and keeps the double when BigReal confirms the zero.

$\color{#3b82f6}\textbf{Value}$: What an expression evaluates to, one variant over every runtime type (value.hpp).

$\color{#3b82f6}\textbf{Variadic call}$: A reduction, gcd or lcm called with several arguments collapses them into one List first, so the three forms below are the same.

```math
\bar{x}(2, 3, 5, 6) = \bar{x}[2, 3, 5, 6] = \bar{x}([2, 3, 5, 6])
```

$\color{#3b82f6}\textbf{VarStore}$: The native store of the session's variables: an assignment writes a value into it, and a later row reads it by name. There is one store for now.

$\color{#3b82f6}\textbf{Write-back}$: Writing a dissolved Math Widget's left slot as text into the parent field at the cursor (\_write_back_at_cursor), the dissolve path when the left slot holds no Math Widget. The cursor ends after the written text.
