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

Source: Example public notes

---

# Flow

::: flow wide
lane: Upstream
[actor] Start | ready {go} -> [system] Middle -.[step].-> [doc] End
lane: Downstream
[muted] Side ..> [highlight] Focus
link: End => Focus : handoff
:::

---

# Columns

::: columns panel
## Left head

Left column text

+++

## Right head

Right column text
:::

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
