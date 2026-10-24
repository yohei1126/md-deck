---
title: md-deck sample
version: "0.2.0"
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
- Output is PDF (PNG optional)

| Piece | Role |
| --- | --- |
| Content `.md` | Slide body |
| Style `.md` | Tokens and optional CSS |
| md-deck | HTML and PDF rendering |

---

# Flow diagrams

**Key Message:** Flow blocks build boxes and arrows; kinds and labels stay in Markdown.

::: flow wide
lane: Pipeline
[actor] Author | writes -> [doc] Slides {md} -.[check].-> [system] md-deck -> [highlight] PDF
lane: Style
[muted] Tokens ..> [system] md-deck
link: Slides => Tokens : bind
:::

Arrow forms: `A -> B`, `A -[label]-> B`, `A ..> B`, `A -.[label].-> B`, and `A <-> B`. Node markers: `[actor]`, `[system]`, `[doc]`, `[muted]`, `[highlight]`. Caption with `Name | caption`; badge with `Name {badge}`.

---

# Two columns

**Key Message:** `::: columns` splits on `+++`; options pick chrome.

::: columns panel
## Content

- Title (`#`)
- Key Message
- Lists and tables

+++

## Style

- YAML tokens
- Optional `css` fence
- Prose for humans
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
