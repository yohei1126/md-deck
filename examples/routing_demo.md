---
title: Routing callouts and chips
version: "0.4.0"
date: "2026-10-24"
lang: en
style: deck_style.md
---

# Orthogonal link routing {#routing .demo .no-cover}

**Key Message:** Cross-lane links bend around nodes; `route=between` uses the gap between lanes.

::: flow wide
lane: North
[actor] Intake {#intake} -> [system] Hub {#hub} -> [doc] Record {#record}
lane: South
[muted] Archive {#archive} -> [highlight] Publish {#publish} [[qa, sign, ship]]
link: record => archive : store [route=between]
link: hub => publish : promote [route=down]
callout: publish : Ready for review [pos=below-left]
:::

Source: md-deck examples

---

# Parallel edges and stacks {#parallel .demo}

**Key Message:** Same-pair arrows offset; `{ A / B }` stacks a column and edges meet the stack mid-box.

::: flow
Origin {#origin} -[solid\npath]-> Target {#target}
Origin -.[dashed\npath].-> Target
Left -> { Upper / Lower } -> Right
:::

::: question
Do the solid and dashed labels stay readable without hand-drawn SVG?
:::

---

# Separate lines stay unconnected {#separate .demo}

**Key Message:** Nodes on their own lines do not chain until you write an arrow or `link:`.

::: flow wide
lane: Top
P {#p}
Q {#q}
R {#r}
lane: Bottom
Target {#t}
link: p => t [route=between]
link: q => t [route=between]
link: r => t [route=between]
:::

---

eyebrow: Worked example [align=end]

# Index, gap label, and a dashed card {#chrome .demo}

**Key Message:** A corner index, an opt-in gap accent, and a dashed card are generic hooks.

::: columns panel
## Quiet {.dashed}

A quieter layer can use a dashed outline.

+++

## Solid

The other card keeps a solid border.
:::

::: flow
① Intake {#in} -> [doc] Check {2} ..> [muted] Filed {#filed}
{#filed} -.[held].-> [highlight] Out {#out} [style=gap]
:::
