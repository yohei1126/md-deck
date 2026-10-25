---
title: Geometry repros
version: "0.0.1"
date: "2026-10-24"
lang: en
style: deck_style.md
---

# 1 Vertical leg crosses a node {.no-cover}

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

---

# above side=left

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=above side=left]
:::

---

# above side=right

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=above side=right]
:::

---

# above side=top

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=above side=top]
:::

---

# above side=bottom

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=above side=bottom]
:::

---

# below side=left

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=below side=left]
:::

---

# below side=right

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=below side=right]
:::

---

# below side=top

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=below side=top]
:::

---

# below side=bottom

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=below side=bottom]
:::

---

# below-left side=left

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=below-left side=left]
:::

---

# below-left side=right

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=below-left side=right]
:::

---

# below-left side=top

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=below-left side=top]
:::

---

# below-left side=bottom

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=below-left side=bottom]
:::

---

# below-right side=left

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=below-right side=left]
:::

---

# below-right side=right

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=below-right side=right]
:::

---

# below-right side=top

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=below-right side=top]
:::

---

# below-right side=bottom

::: flow wide
L -> A {#a} -> R
callout: a : note [pos=below-right side=bottom]
:::

---

# left side=left

::: flow wide
Spacer -> A {#a} -> R
callout: a : note [pos=left side=left]
:::

---

# left side=right

::: flow wide
Spacer -> A {#a} -> R
callout: a : note [pos=left side=right]
:::

---

# left side=top

::: flow wide
Spacer -> A {#a} -> R
callout: a : note [pos=left side=top]
:::

---

# left side=bottom

::: flow wide
Spacer -> A {#a} -> R
callout: a : note [pos=left side=bottom]
:::

---

# right side=left

::: flow wide
L -> A {#a} -> Spacer
callout: a : note [pos=right side=left]
:::

---

# right side=right

::: flow wide
L -> A {#a} -> Spacer
callout: a : note [pos=right side=right]
:::

---

# right side=top

::: flow wide
L -> A {#a} -> Spacer
callout: a : note [pos=right side=top]
:::

---

# right side=bottom

::: flow wide
L -> A {#a} -> Spacer
callout: a : note [pos=right side=bottom]
:::

---

# 17 Straight fan-in four sources

::: flow straight
P {#p17}
Q {#q17}
R {#r17}
S {#s17}
T {#t17}
{#p17} -> {#t17}
{#q17} -> {#t17}
{#r17} -> {#t17}
{#s17} -> {#t17}
:::

---

# 18 Orthogonal fan-in four sources

::: flow
P {#p18}
Q {#q18}
R {#r18}
S {#s18}
T {#t18}
{#p18} -> {#t18}
{#q18} -> {#t18}
{#r18} -> {#t18}
{#s18} -> {#t18}
:::

---

# 19 Straight fan-out same row

::: flow straight
Source {#t19}
Alpha {#x19}
Beta {#y19}
Gamma {#z19}
{#t19} -> {#x19}
{#t19} -> {#y19}
{#t19} -> {#z19}
:::

---

# Second dashed edge keeps a clear corridor

::: flow spread
lane: Upper
[doc] One {#u1} -> [doc] Two {#u2} -> [doc] Three {#u3} -> [doc] Four {#u4}
lane: Lower
[doc] Five {#l1} -> [doc] Six {#l2} -> [doc] Seven {#l3} -> [doc] Eight {#l4}
link: l4 ..> l2 : return [route=up]
link: u3 ..> l3 : direct [route=down]
:::

---

# Vertical gap label

::: flow
lane: Upper
[doc] Alpha {#ga}
lane: Lower
[doc] Beta {#gb}
link: ga ..> gb : gap [route=down style=gap]
:::

---

# Corner index sits outside the title

::: flow
① Intake {#in} -> Review {2}
:::

---

# Dashed stroke versus gap emphasis

::: flow
Ordinary {#ord} ..> Plain {#pln}
Gap {#gp} -.[held].-> Mark {#mk} [style=gap]
:::

---

# Dashed card outline

::: columns panel
## Quiet {.dashed}

A short note.

+++

## Solid

A short note.
:::

---

# Same-row around landing

::: flow
lane: Row
Left {#sld} -> Mid {#smd} -> Right {#srd}
link: sld => srd : under [route=down]
link: srd => sld : over [route=up]
:::

---

# Lane label misses the vertical link

::: flow
lane: Upper
Alpha {#la}
lane: Insurance
Beta {#lb}
link: la => lb : drop [route=down]
:::

---

# Lane label shifts off a vertical link

::: flow
lane: Upper
One {#na} -> Two {#nb} -> Three {#nc} -> Four {#nd}
lane: This lane label is wider than one box
Five {#ne} -> Six {#nf} -> Seven {#ng} -> Eight {#nh}
link: na => ne : drop [route=down]
:::
