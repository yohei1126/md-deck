---
title: Diagram patterns
version: "0.1.0"
date: "2026-10-25"
lang: en
style: deck_style.md
subtitle: Before and after for compare, branch, and steps
---

# Diagram patterns

**Key Message:** Boxes, arrows, and branches stay readable when the words stay short.

Paired slides below show a weak layout and the recipe to use instead. Notes on what changed are in docs/DIAGRAMS.md in the md-deck repo.

Source: md-deck examples

---

# Compare, before

**Key Message:** Long paragraphs in two columns hide the comparison.

::: columns
## How it works today

The team copies text into a document, edits it in several places, and exports a PDF whenever someone asks. Readers cannot tell which export is current.

+++

## How it could work

One Markdown file is checked in CI and the PDF is rebuilt from the same bytes, so review comments point at a line instead of a screenshot.
:::

The two sides are not parallel, so the eye has to re-parse each paragraph.

---

# Compare, after

**Key Message:** A comparison is two boxes with the same kind of line in each.

::: columns panel
## Current

- Many owners
- Manual export
- Hard to diff

+++

## Proposed

- One generator
- Same PDF bytes
- Check in CI
:::

`panel` keeps the boxes. Three bullets, same grammar, no arrow between them.

---

# Branch, before

**Key Message:** A fork buried in one label does not show the branch.

::: flow
Start -> Choose keep or change
:::

The second box is a sentence. There is no arrow into each outcome.

---

# Branch, after

**Key Message:** Each outcome is its own box, with its own arrow.

::: flow
Start {#start}
{ Keep / Change }
{#start} -> Keep
{#start} -> Change
:::

The stack is the branch. Separate edges fan into each box instead of one arrow into the pair.

---

# Steps, before

**Key Message:** A numbered list reads as prose, not as three steps.

1. Someone gathers notes from several places and pastes them into a document that keeps growing.
2. A reviewer reads the whole document and tries to decide what changed since last time.
3. Another person exports a PDF by hand and emails it, so the next reader is never sure which file is current.

---

# Steps, after

**Key Message:** Three short boxes in a row are the step bone.

::: flow wide
Collect -> Decide -> Record
:::

`wide` keeps the row on one line. Labels are names, not sentences.

---

# 骨子を先に見せる\n色は抑えて残す {.cover}

**Key Message:** A cover break is an explicit `\n` between phrases of similar length.

Automatic wrapping would cut a Japanese title mid-phrase. The backslash-n is the break.
