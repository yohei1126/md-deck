---
title: Good Deck
version: "1.0.0"
date: "2026-01-15"
lang: en
style: deck_style.md
---

# Welcome {#welcome .intro}

**Key Message:** This deck is valid.

A short body line.\
With a hard break.

- Plain item
- Highlighted item
  {: .highlight}

Source: Example public notes

---

# Flow

::: flow wide
lane: Upstream
[actor] Start {#start} | ready {go} -> [system] Middle -[lab\nel]-> [doc] End [[alpha, beta]]
lane: Downstream
[muted] Side ..> [highlight] Focus {#focus}
link: End => focus : handoff [route=between]
link: start ..> Focus : alt
callout: focus : Check here [pos=below-right]
:::

---

# Parallel and stack

::: flow
A -[solid\npath]-> B
A -.[dashed\npath].-> B
C -> { Upper / Lower } -> D
:::

---

# Columns with nested flow

::: columns panel
## Left head

::: flow
In -> Out
:::

+++

## Right head

Right column text
:::

---

# Tables

|  | Alpha | Beta |
| --- | --- | --- |
| Row one | a1 | b1 |
| Row two | a2 | b2 |

---

# Plain columns

::: columns plain
### A

One

+++

### B

Two
:::

---

# Question

::: question
Does this validate?
Second line inside the block.
:::

::: source
Extra source note for the footer.
:::
