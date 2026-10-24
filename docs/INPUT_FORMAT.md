# Input contract

md-deck accepts two Markdown files from a deck repository: slides and style. `md-deck check` validates the contract without Chromium and prints every problem as `file:line: message`. `md-deck build` runs the same checks first and refuses to render on failure.

Machine-readable schemas ship in [`schemas/slides.schema.json`](../schemas/slides.schema.json) and [`schemas/style.schema.json`](../schemas/style.schema.json). Editors and other tools can reuse them; the CLI validates with `jsonschema`.

Stable HTML classes and data attributes for style CSS are listed in [HOOKS.md](HOOKS.md).

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
| `lang` | yes | Language tag, at least 2 characters (`ja`, `en`, …). Sets `<html lang>` and default label tokens |
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

All other tokens in the [style guide](STYLE_GUIDE.md) are optional and fall back to plain defaults when omitted. Unknown token names are errors. Values are type-checked (CSS colours, sizes with optional `px`/`rem`/`em`/`%`, `0` / `none` where allowed, font weights, line-height, label strings, placement enums).

## Referenced assets

Relative image and link targets in the slides file must exist on disk next to the slides (or under that directory). `http(s):`, `mailto:`, and in-page `#` anchors are left alone. Absolute local paths (`/…`, `C:\…`) are errors.

## Per-slide Markdown rules

Deck-specific:

- At least one non-empty slide; a trailing `---` that creates an empty slide is an error
- Exactly one H1 (`# …`) per slide; no H1 inside `:::` blocks
- Optional heading attributes via `attr_list`: `# Title {#id .class}` (sets slide `id` / classes and the `h1` attributes)
- Heading levels must not skip (H1 then H4 is an error)
- At most one `**Key Message:**` line per slide
- Known blocks: `::: question`, `::: flow`, `::: columns`, `::: source`
- Block options after the kind are validated per kind; unknown options fail with `file:line`
  - `flow`: `wide`
  - `columns`: `plain`, `panel`
  - `question` / `source`: no options
- Every `:::` opener needs a matching closer; stray closers and `::` / `::::` lines fail
- Nested blocks are forbidden, except `::: flow` inside `::: columns` (one level only)
- Flow: at least two nodes; empty nodes in `A -> -> B` fail; unknown `[kind]` markers fail; unknown `route=` / `pos=` values fail; duplicate `{#id}` fails
- Columns: at least two non-empty parts split by a `+++` line; `+++` outside `columns` fails
- Question and source blocks must not be empty
- Tables: every row has the same column count; an empty first header cell promotes the first body column to `th[scope=row]`
- Fenced code blocks must close
- Raw HTML is forbidden unless `--allow-html`
- Hard line breaks: a backslash at end of line (`\`), or `\n` inside flow titles, captions, badges, and arrow labels. Inside `question` / `source` blocks, single newlines also become breaks
- List item classes via `attr_list` on the next line stay on `<li>` without forcing a wrapping `<p>` for simple items

Generic hygiene (via [pymarkdownlnt](https://github.com/jackdewinter/pymarkdown) on each slide body): heading increment (MD001), list indent (MD005/MD007), hard tabs (MD010), list marker spacing (MD030), fenced-code blanks/language/style (MD031/MD040/MD046). A committed [`pymarkdown.json`](../pymarkdown.json) documents the repo defaults; `md-deck check` applies its own enable/disable set so deck-specific rules stay authoritative for H1 count and HTML.

## Flow syntax

```markdown
::: flow wide
lane: Intake
[actor] Writer {#writer} | drafts -> [doc] Spec {#spec} {v1} -[review\npass]-> [system] Builder [[lint, pack]]
lane: Publish
[muted] Archive ..> [highlight] PDF {#pdf}
link: Builder => pdf : emit [route=down]
link: spec ..> Archive : store
callout: pdf : Ready to ship [pos=below]
:::
```

| Construct | Syntax |
| --- | --- |
| Solid arrow | `A -> B` |
| Labelled solid | `A -[label]-> B` |
| Dashed arrow | `A ..> B` |
| Labelled dashed | `A -.[label].-> B` |
| Bidirectional pair | `A <-> B` or `A <-[label]-> B` |
| Node kind | `[actor]`, `[system]`, `[doc]`, `[muted]`, `[highlight]` before the name |
| Node id | `Name {#id}` (stable `data-node` / link target; works with duplicate titles and `\n` breaks) |
| Caption (second line) | `Name \| caption` |
| Badge | `Name {badge}` (must not start with `#`) |
| Chips inside the node | `Name [[chip1, chip2, chip3]]` |
| Line break in node / label / badge | `\n` or a trailing `\` |
| Lane | `lane: Label` starts a lane |
| Cross-lane link | `link: From => To : optional label [route=down]` (also `->` / `..>`; routes: `auto`, `up`, `down`, `left`, `right`) |
| Callout | `callout: NodeId : text [pos=below]` (`above` / `below` / `left` / `right`) |
| Stacked column | `A -> { Upper / Lower } -> B` |
| Parallel edges | Repeat the same pair on separate lines; strokes offset and labels separate |

Existing `A -> B -> C` chains and one-node-per-line lists keep working. Cross-lane links draw as orthogonal (right-angled) paths that route around nodes; `route=` picks the corridor when the default is ambiguous.

## Columns and nesting

```markdown
::: columns panel
## Left

::: flow
A -> B
:::

+++

## Right

Notes
:::
```

Only `flow` may nest inside `columns`. Question, source, or another columns block inside columns still fails the check.

## Sources and footer

- `Source: …` or `出典:…` / `出典：…` on its own line moves into the footer with class `.source`
- Or `::: source` … `:::` for a longer note
- Page numbers render automatically as `n / total` with class `.page-number`
- `page_number_placement` (`bottom-right` default, also `bottom-left`, `bottom-center`) positions the page mark independently of the source footer

## Labels

Style tokens `label_question` and `label_key_message` set the visible label text. When omitted, defaults follow `lang`:

| `lang` | Question | Key Message |
| --- | --- | --- |
| `ja` (and `ja-*`) | 議論の問い | キーメッセージ |
| other | Question | Key Message |

`question_label_placement` is `inline` by default (label in the first paragraph) or `block` (label on its own line above the body).

## Commands

```bash
uv run md-deck check examples/sample.md
uv run md-deck check path/to/slides.md --style path/to/style.md
uv run md-deck build examples/sample.md -o out/sample.pdf
```
