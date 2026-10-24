---
title: Geometry repros
version: "0.0.1"
date: "2026-10-24"
lang: en
style: deck_style.md
---

# 1 Vertical leg crosses a node

::: flow wide
lane: A
A1 -> A2 -> A3 {#a3}
lane: B
B1 {#b1} -> B2 -> B3
link: a3 => b1 : x [route=down]
:::

---

# 2 Fan-in links

::: flow wide
lane: Top
P {#p}
Q {#q}
R {#r}
lane: Bottom
Target {#t}
link: p => t
link: q => t
link: r => t
:::

---

# 3 Parallel multi-line label

::: flow
S {#s} -[one\ntwo\nthree]-> T {#t}
S -.[dash].-> T
callout: t : note text [pos=below]
:::

---

# 4 Stack edges

::: flow
L -> { Up / Down } -> R
:::

---

# 5 Chips only and slash

::: flow
A -> [[x, y]] -> B
N [[a/b, c]] -> M
:::

---

# 6 Shrink margin

::: question
Line one keeps this slide nearly full so shrink-to-fit must honour the question box bottom margin before the footer.
\
Line two adds height.
\
Line three adds height.
\
Line four adds height.
\
Line five adds height.
\
Line six adds height.
\
Line seven adds height.
\
Line eight adds height.
\
Line nine adds height.
\
Line ten adds height.
\
Line eleven adds height.
\
Line twelve adds height.
:::
