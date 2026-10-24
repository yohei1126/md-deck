---
title: md-deck sample
version: "0.3.0"
date: "2026-10-24"
lang: en
style: deck_style.md
subtitle: Input contract and syntax walkthrough
author: md-deck
audience: Tool users
---

# Welcome to md-deck {#welcome .intro}

**Key Message:** One Markdown file yields the same 16:9 PDF every time.

md-deck owns layout and the build. Colours, type, and chrome live in the deck's style Markdown.

Source: md-deck examples

---

# Lists and tables

**Key Message:** Ordinary Markdown lists and tables work as-is.

- Slides are Markdown
- Separators are `---`
- Highlighted list item
  {: .highlight}

|  | Content | Style |
| --- | --- | --- |
| File | `.md` slides | `.md` tokens |
| Role | Slide body | Theme and CSS |
| Tool | md-deck | HTML and PDF |

The empty corner cell marks the first column as row headers (`th[scope=row]`).

---

# Flow diagrams

**Key Message:** Flow blocks build boxes and arrows; kinds, ids, chips, and routes stay in Markdown.

::: flow wide
lane: Pipeline
[actor] Author {#author} | writes -> [doc] Spec {#spec} {md} -[review\npass]-> [system] Builder [[lint, render]]
lane: Style
[muted] Tokens {#tokens} ..> [highlight] PDF {#pdf}
link: spec => tokens : bind [route=down]
link: author ..> pdf : emit
callout: pdf : Ship it [pos=below]
:::

Arrow forms: `A -> B`, `A -[label]-> B`, `A ..> B`, `A -.[label].-> B`, and `A <-> B`. Node markers: `[actor]`, `[system]`, `[doc]`, `[muted]`, `[highlight]`. Caption with `Name | caption`; badge with `Name {badge}`; id with `Name {#id}`; chips with `Name [[a, b]]`. Cross-lane links: `link: From => To : label [route=down]`.

---

# Parallel edges and stacks

**Key Message:** Parallel arrows offset automatically; `{ A / B }` stacks nodes in one column.

::: flow
Source -[solid]-> Target
Source -.[dashed].-> Target
Left -> { Upper / Lower } -> Right
:::

---

# Columns with nested flow

**Key Message:** `::: columns` may contain one nested `::: flow` per column; other nesting stays forbidden.

::: columns panel
## Content path

::: flow
Draft -> Review -> Publish
:::

+++

## Style path

::: flow
Tokens -> CSS -> PDF
:::
:::

::: columns plain
### Bare left

No card border from the generator.

+++

### Bare right

Style CSS can still colour these.
:::

---

# Questions and breaks

**Key Message:** Discussion boxes use `::: question`; a trailing `\` forces a line break.

Line one continues\
on the next line without trailing spaces.

::: question
Try building this sample.
Change one style token and compare the PDF.
:::

::: source
md-deck examples (generic sample content)
:::
