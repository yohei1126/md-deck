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

---

# 7 Fan-in ports and between orthogonal

::: flow wide
lane: Top
P {#p7}
Q {#q7}
R {#r7}
lane: Bottom
Wide target node with a long title so it spans the row {#t7}
link: p7 => t7 [route=between]
link: q7 => t7 [route=between]
link: r7 => t7 [route=between]
:::

---

# 8 Same-row edges skip intermediates

::: flow
P {#p8}
Q {#q8}
R {#r8}
T {#t8}
{#p8} -> {#t8}
{#q8} -> {#t8}
{#r8} -> {#t8}
:::

---

# 9 Cross-lane id arrow

::: flow
lane: Top
A {#a9}
lane: Bottom
B {#b9}
{#a9} -> {#b9}
:::

---

# 10 Callout side and gap

::: flow wide
[doc] Left {#l10} | a caption under the left node -> Right {#r10}
callout: r10 : a fairly long callout note text [pos=below-left side=right]
:::

---

# 11 Callout side=left below-right

::: flow wide
Anchor {#a11} -> Middle -> Right
callout: a11 : a callout note [pos=below-right side=left]
:::

---

# 12 Straight fan-in edges

::: flow wide straight
lane: Top
P {#p12}
Q {#q12}
R {#r12}
lane: Bottom
Wide target node with a long title so it spans the row {#t12}
link: p12 => t12 [route=between]
link: q12 => t12 [route=between]
link: r12 => t12 [route=between]
:::

---

# 13 Per-edge straight shape

::: flow wide
lane: Top
P {#p13}
Q {#q13}
lane: Bottom
Target {#t13}
link: p13 => t13 [route=between shape=straight]
link: q13 => t13 [route=between]
:::

---

# 14 Straight skip same-row intermediates

::: flow wide
A {#a14} -> B {#b14} -> C {#c14} -> D {#d14}
{#a14} -> {#d14} [shape=straight]
:::

---

# 15 Straight fan-in same row

::: flow straight
Alpha {#x15}
Beta {#y15}
Gamma {#z15}
Target {#t15}
{#x15} -> {#t15}
{#y15} -> {#t15}
{#z15} -> {#t15}
:::

---

# 16 Callout above side=left

::: flow wide
Left -> Anchor {#a16} -> Right
callout: a16 : above note [pos=above side=left]
:::
