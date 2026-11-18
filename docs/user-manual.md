# TCalc user manual

## Introduction

TCalc is a scientific calculator that reads a whole expression, written as text with LaTeX in it, and evaluates it as you type. Integers and fractions stay exact, and a number too large for a 64-bit float is carried to 50 significant digits.

## Usage

### General usage

- **Result line.** The result updates on every key. Enter, **=** or **↵** commits the row to the history and starts a new one.
- **History.** Every committed row is kept, also between sessions. The history shows the rows in one of three modes: Math (rendered), Flat (formatted text) or Raw (the LaTeX). Clear History empties it.
- **Undo, cut and paste.** The Edit menu has Undo, Redo, Cut, Copy and Paste for the row.
- **Keypad presets.** View, Keypad Preset picks a layout: Simple shows the numpad; Science adds the trig and power pad, the functions pad and the angle buttons. A layout you arrange can be saved as a preset of its own.

### Typing an expression

A row is plain text with LaTeX in it. A LaTeX construct such as **\frac{1}{3}** turns into the rendered $\frac{1}{3}$ as soon as it is complete, and a function name with a symbol turns into that symbol: **sqrt** becomes **√**.

- Precedence is the usual one: **2+3\*4** is **14**.
- A number, a constant, a variable or a closing paren next to the next operand multiplies it: **2π**, **2(3+4)**, **(1+2)(3+4)**, **2A**.
- A function of one argument takes its argument with or without parentheses: **sqrt 16** and **√(16)** are both **4**.
- A function of two or more arguments is always called: **mod(7,3)**, not **7 mod 3**.
- Nest an exponent inside the braces of the one below it: **2^{3^{2}}** is $2^{3^{2}} = 512$.

### LaTeX

A body or an argument goes in braces.

| Construct | Type | Renders as | Example | Result |
|---|---|---|---|---|
| Fraction | \frac{a}{b} | $\frac{a}{b}$ | \frac{1}{3}+\frac{1}{6} | 0.5 |
| Power | x^{n} | $x^{n}$ | 2^{10} | 1024 |
| Square root | \sqrt{x} | $\sqrt{x}$ | \sqrt{16} | 4 |
| Root | \sqrt[n]{x} | $\sqrt[n]{x}$ | \sqrt[3]{-8} | -2 |
| Subscript | x_{i} | $x_{i}$ | x_{0}=3 | 3 |
| Sum | \sum_{n=a}^{b} body | $\sum_{n=a}^{b}$ | \sum_{n=1}^{100} n | 5050 |
| Product | \prod_{n=a}^{b} body | $\prod_{n=a}^{b}$ | \prod_{n=1}^{5} n | 120 |

- The body of a sum or a product is the term right after it: $\sum_{n=1}^{10} n^{2} = 385$, and $\sum_{n=1}^{3} (n+1)! = 32$.
- The limits are whole numbers.
- The bound variable cannot be a constant's name: $\sum_{k=1}^{4} k^{2}$ is an error, because *k* is Boltzmann's constant.

## Keypads

Each button inserts its function at the cursor; the same function can be typed by its name. Hovering over a button shows its name.

### Numpad

| Button | Function | Typed as |
|---|---|---|
| 0 to 9, . | digits and the decimal point | |
| + − · ÷ | add, subtract, multiply, divide | + - \* / |
| % | percent | % |
| ( ) | parentheses | ( ) |
| +/- | toggle the sign of the last number | |
| ⌫ | delete left of the cursor | Backspace |
| C | clear the row | Delete |
| =, ↵ | commit the row | Enter |

### Trig and power pad

Shift switches the buttons that have a second function to it; Hyp turns sin, cos and tan, and their inverses, into the hyperbolic functions.

| Button | Shift | Function | Typed as |
|---|---|---|---|
| sin cos tan | asin acos atan | trig and inverse trig, in the current angle unit | sin cos tan asin acos atan |
| Hyp + sin cos tan | asinh acosh atanh | hyperbolic and inverse hyperbolic | sinh cosh tanh asinh acosh atanh |
| x² | x³ | square, cube | ² ³, sqr cube |
| √x | ³√x | square root, cube root | √ ³√, sqrt cbrt |
| xʸ | x¹ᐟʸ | power, root | ^, ⌄ |
| ∠ | | $\cos\theta + i\sin\theta$ | polar |
| π | | pi | pi |

### Functions pad

| Button | Function | Typed as | Example | Result |
|---|---|---|---|---|
| mod | remainder, with the sign of the dividend | mod | mod(-7,3) | -1 |
| intDiv | integer division, truncated | intdiv | intdiv(-7,2) | -3 |
| nPr | permutations | nPr, permute | nPr(5,2) | 20 |
| nCr | combinations | nCr, choose | nCr(5,2) | 10 |
| x! | factorial | !, fact, factorial | 5! | 120 |
| Γ | gamma, Γ(n) = (n−1)! | gamma | Γ(5) | 24 |
| log | log base 10 | log | log(100) | 2 |
| 10ˣ | power of ten | ⏨ | ⏨3 | 1000 |
| ln | natural log | ln | ln(e) | 1 |
| eˣ | $e^{x}$ | exp | exp(1) | 2.718281828459045 |
| 1/x | reciprocal | ⁻¹ | 2⁻¹ | 0.5 |
| trunc | toward zero | trunc, int | trunc(2.7) | 2 |
| ⌊ ⌈ | floor, ceiling | floor, ceil | floor(-2.5) | -3 |

### Custom pads

View, Keypads, Add Custom Pad builds a pad from the buttons you pick.

## Functions without a button

| Function | Typed as | Example | Result |
|---|---|---|---|
| greatest common divisor, least common multiple | gcd lcm | gcd(12,18,30) | 6 |
| mean, median | mean median, x̄ x̃ | mean(1,2,3,4) | 2.5 |
| smallest, largest | min max | max(3,1,2) | 3 |
| sum of the items | sum, Σ | sum(1,2,3) | 6 |
| sample, population variance | var varp, s² σ² | var(1,2,3,4) | 1.666666666666667 |
| sample, population standard deviation | std stdp, s σ | stdp(1,2,3,4) | 1.118033988749895 |

## Variables

**A=5** stores 5 in *A*, and every row after it can read *A*. A name can be assigned again, and a row that reads it then sees the new value.

- **A=7**, then **B=A+1**: *B* is **8**.
- **2A** and **AB** multiply: with *A* = 7 and *B* = 8, **AB** is **56**.
- A subscript makes a family of names: $x_{0}=3$, $x_{1}=4$, then $x_{0}+x_{1}$ is **7**.
- Reading a name that was never assigned is an error: *undefined variable x*.

## Lists and points

- **[1,2,3]** is a list and **(1,2)** is a point.
- The statistics functions take a list or the items themselves: **mean[1,2,3,4]** and **mean(1,2,3,4)** are both **2.5**.
- A list of points is reduced per coordinate: **mean[(1,2),(3,4)]** is **(2, 3)**.
- A list cannot hold lists, and arithmetic on a whole list is not defined: **[1,2]+1** is an error.

## Angles

The Deg, Rad and Grad buttons set the angle unit. Trig functions read their argument in it, and inverse trig functions answer in it.

- In Deg, $\sin(30) = 0.5$, $\tan(45) = 1$ and $\arcsin(0.5) = 30$.
- In Rad, $\sin(\pi) = 0$ and $\cos(\pi/3) = 0.5$.

These are exact, not rounded: where the value is rational (sine and cosine at multiples of 30°, tangent at multiples of 45°), TCalc returns that value instead of a floating point approximation. $\tan(\pi/2)$ is an error, since the tangent has no value there.

## Memory operations

| Button | Function |
|---|---|
| MC | clear the memory |
| MR | insert the memory into the row |
| MS | store the current result |
| M+ | add the current result to the memory |

The memory holds one number, not a list.

## Comments on specific functions

### Percent

**%** divides the number before it by 100, whatever the operator before it: **200\*10%** is **20**, and **150+50%** is **150.5**, not 225.

### Mod and IntDiv

Both truncate toward zero: **intdiv(-7,2)** is **-3**, and **mod(-7,3)** is **-1**, so the remainder takes the sign of the dividend.

### Unary minus

The +/- button toggles the sign of the last number; pressing it again flips it back. A typed minus at the start of a term binds weaker than a power or a root, so it applies after them:

- **-4+2** is **-2**.
- **-4⌄2** is $-\sqrt{4} = -2$.
- **(-4)⌄2** makes the base negative: $\sqrt{-4} = 2i$.

### Scientific notation and the constant e

- **10e** is $10 \cdot e \approx 27.18$.
- **10e+0**, with no space, is scientific notation: $10 \times 10^{0} = 10$.
- **10e + 0**, with spaces, is $10 \cdot e + 0$ again.

Use a space, an explicit **\*** or parentheses when you mean the constant.

### Factorial

The factorial of a whole number is exact: an integer up to $20!$, and a BigReal past it, exact while the result has at most 50 significant digits. Up to $100!$ the value comes from Boost's correctly rounded factorial table ([Boost.Math factorial](https://www.boost.org/doc/libs/release/libs/math/doc/html/math_toolkit/factorials/sf_factorial.html)); past it, from the gamma function at 50 digits: $1000! \approx 4.023872600770938 \times 10^{2567}$.

Any other input goes through the gamma function, $n! = \Gamma(n + 1)$, so a fraction has a factorial too: $(1/2)! = \sqrt{\pi}/2 \approx 0.8862269254527581$. A negative integer is a pole of the gamma function and has none: $(-1)!$ is a math error. The gamma function itself is the C library's [tgamma](https://git.musl-libc.org/cgit/musl/tree/src/math/tgamma.c), a [Lanczos approximation](https://mathworld.wolfram.com/LanczosApproximation.html).

## Questions and answers

### What about precision?

TCalc keeps a number exact as long as it can and widens it only when it has to.

- **Exact fractions.** Integers and fractions are kept as exact rationals: $0.1+0.2 = 0.3$, and $\frac{1}{3}+\frac{1}{3}+\frac{1}{3} = 1$.
- **Floating point.** A result that is irrational is a 64-bit floating point number with about 16 significant digits: $2^{0.5} \approx 1.414213562373095$.
- **50 digits.** A number past the 64-bit range becomes a BigReal, a decimal floating point number with 50 significant digits ([Boost.Multiprecision cpp_dec_float](https://www.boost.org/doc/libs/release/libs/multiprecision/doc/html/boost_multiprecision/tut/floats/cpp_dec_float.html)). $10^{400}$, **1e400** and $(1/2)^{2000}$ all have a value. Fifty digits is the limit: $10^{400}+1-10^{400}$ is $0$, because the 1 is the 401st digit.

### Does it compute with complex numbers?

Yes. *i* is the imaginary unit, and a result that leaves the real numbers turns complex on its own: $\sqrt{-4} = 2i$, $(1+2i)(3-i) = 5+5i$ and $e^{i\pi} = -1$.

### What does the status line under the result mean?

It names the problem when there is no result:

- **Math error:** the value does not exist, as in $1/0$, $(-1)!$ or $\tan(\pi/2)$ in Rad, or the operation is not defined for that kind of value, as in **[1,2]+1**.
- **Invalid expression:** the row cannot be read, as in an undefined variable, a fractional sum limit, or **mod** used as an infix operator.

## Command reference

### View menu

- **Theme:** Light, Dark, System Default, or a custom theme.
- **Keypad Preset:** Simple or Science, or a layout you saved.
- **Keypads:** show or hide the numpad, the functions pad and the trig and power pad, and add custom pads.
- **Angle Buttons, History:** show or hide them.
- **Restore Default Layout.**

### Settings menu

- **Configure Keyboard Shortcuts.**
- **Configure TCalc.**
