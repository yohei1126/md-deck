# Input contract

md-deck accepts two Markdown files from a deck repository: slides and style. `md-deck check` validates the contract without Chromium and prints every problem as `file:line: message`. `md-deck build` runs the same checks first and refuses to render on failure.

Machine-readable schemas ship in [`schemas/slides.schema.json`](../schemas/slides.schema.json) and [`schemas/style.schema.json`](../schemas/style.schema.json). Editors and other tools can reuse them; the CLI validates with `jsonschema`.

## Minimal valid example

`slides.md`:

```markdown
---
title: Demo deck
version: "0.1.0"
date: "2026-10-24"
lang: en
style: deck_style.md
---

# First slide

**Key Message:** One idea per slide.

Body text here.
```

`deck_style.md`:

```markdown
---
color_background: "#ffffff"
color_text: "#000000"
color_title: "#000000"
font_family: "sans-serif"
font_size_body: 22
---

# Style notes for humans (ignored by the generator)
```

```bash
uv run md-deck check slides.md
uv run md-deck build slides.md -o out.pdf
```

`--style path` overrides the front matter `style:` value when you need to point at another file.

## Slides front matter

| Key | Required | Rules |
| --- | --- | --- |
| `title` | yes | Non-empty string |
| `version` | yes | Non-empty string |
| `date` | yes | ISO `yyyy-mm-dd` and a real calendar day |
| `lang` | yes | Language tag, at least 2 characters (`ja`, `en`, …) |
| `style` | yes | Relative path to the style Markdown; file must exist |
| `subtitle` | no | String |
| `author` | no | String |
| `audience` | no | String |

Unknown keys are errors. Absolute `style` paths are errors.

## Style front matter

Required tokens (must be present):

| Token | Meaning |
| --- | --- |
| `color_background` | Page background |
| `color_text` | Body text colour |
| `color_title` | Title / accent colour |
| `font_family` | Font stack |
| `font_size_body` | Base body size |

All other tokens in the [style guide](STYLE_GUIDE.md) are optional and fall back to plain defaults when omitted. Unknown token names are errors. Values are type-checked (CSS colours, positive sizes with optional `px`/`rem`/`em`/`%`, font weights, line-height).

## Referenced assets

Relative image and link targets in the slides file must exist on disk next to the slides (or under that directory). `http(s):`, `mailto:`, and in-page `#` anchors are left alone. Absolute local paths (`/…`, `C:\…`) are errors.

## Per-slide Markdown rules

Deck-specific:

- At least one non-empty slide; a trailing `---` that creates an empty slide is an error
- Exactly one H1 (`# …`) per slide; no H1 inside `:::` blocks
- Heading levels must not skip (H1 then H4 is an error)
- At most one `**Key Message:**` line per slide
- `::: question` / `flow` / `columns` only; unknown kinds (e.g. `::: note`) fail
- Every `:::` opener needs a matching closer; stray closers and `::` / `::::` lines fail
- No nested blocks
- Flow: at least two nodes; empty nodes in `A -> -> B` fail
- Columns: at least two non-empty parts split by a `+++` line; `+++` outside `columns` fails
- Question blocks must not be empty
- Tables: every row has the same column count
- Fenced code blocks must close
- Raw HTML is forbidden unless `--allow-html`

Generic hygiene (via [pymarkdownlnt](https://github.com/jackdewinter/pymarkdown) on each slide body): heading increment (MD001), list indent (MD005/MD007), hard tabs (MD010), list marker spacing (MD030), fenced-code blanks/language/style (MD031/MD040/MD046). A committed [`pymarkdown.json`](../pymarkdown.json) documents the repo defaults; `md-deck check` applies its own enable/disable set so deck-specific rules stay authoritative for H1 count and HTML.

## Commands

```bash
uv run md-deck check examples/sample.md
uv run md-deck check path/to/slides.md --style path/to/style.md
uv run md-deck build examples/sample.md -o out/sample.pdf
```
