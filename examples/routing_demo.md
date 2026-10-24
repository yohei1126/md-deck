---
title: Routing callouts and chips
version: "0.3.0"
date: "2026-10-24"
lang: en
style: deck_style.md
---

# Orthogonal link routing {#routing .demo}

**Key Message:** Cross-lane links bend around nodes; `route=` picks the corridor.

::: flow wide
lane: North
[actor] Intake {#intake} -> [system] Hub {#hub} -> [doc] Record {#record}
lane: South
[muted] Archive {#archive} -> [highlight] Publish {#publish} [[qa, sign, ship]]
link: record => archive : store [route=down]
link: hub => publish : promote [route=down]
callout: publish : Ready for review [pos=below]
:::

Source: md-deck examples

---

# Parallel edges and stacks {#parallel .demo}

**Key Message:** Same-pair arrows offset; `{ A / B }` stacks a column.

::: flow
Origin {#origin} -[solid\npath]-> Target {#target}
Origin -.[dashed\npath].-> Target
Left -> { Upper / Lower } -> Right
:::

::: question
Do the solid and dashed labels stay readable without hand-drawn SVG?
:::
