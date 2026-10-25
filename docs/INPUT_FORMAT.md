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
- H1 line break: `\n` inside the heading (`# First phrase\nSecond phrase`) becomes a `<br>` in `.title`. An ATX heading cannot wrap with a trailing `\`. Cover rules (the first slide, `{.cover}`, and `{.no-cover}`) are in [VISUAL_POLICY.md](VISUAL_POLICY.md)
- Heading levels must not skip (H1 then H4 is an error)
- At most one `**Key Message:**` line per slide
- Known blocks: `::: question`, `::: flow`, `::: columns`, `::: source`
- Block options after the kind are validated per kind; unknown options fail with `file:line`
  - `flow`: `wide`, `straight`, `steps`
  - `columns`: `plain`, `panel`
  - `question` / `source`: no options
- Every `:::` opener needs a matching closer; stray closers and `::` / `::::` lines fail
- Nested blocks are forbidden, except `::: flow` inside `::: columns` (one level only)
- Flow: at least two nodes; empty nodes in `A -> -> B` fail; unknown `[kind]` markers fail; unknown `route=` / `pos=` / `shape=` / `side=` values fail; duplicate `{#id}` fails
- Columns: at least two non-empty parts split by a `+++` line; `+++` outside `columns` fails
- Question and source blocks must not be empty
- Tables: every row has the same column count; an empty first header cell promotes the first body column to `th[scope=row]`
- Fenced code blocks must close
- Raw HTML is forbidden unless `--allow-html`
- Hard line breaks: a backslash at end of line (`\`), or `\n` inside flow titles, captions, badges, arrow labels, and H1 titles. Inside `question` / `source` blocks, single newlines also become breaks
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
| Chips inside the node | `Name [[chip1, chip2]]` (split on `,` only; write `\,` for a literal comma; `/` stays inside the chip). A chips-only node `[[a, b]]` is allowed |
| Line break in node / label / badge | `\n` or a trailing `\` |
| Lane | `lane: Label` starts a lane. `lane:` with no label starts an unlabelled row. Optional `[align=start\|center\|end]` moves a shorter lane inside the group (default `start` keeps columns aligned across lanes) |
| Cross-lane link | `link: From => To : optional label [route=between]` (also `->` / `..>`; routes below). Optional `shape=straight` (or `orthogonal`) per link. A bare `{#id} -> {#other}` that names nodes already defined in other lanes resolves the same way |
| Edge shape on a chain | Trailing opts on the destination: `A -> B [shape=straight]` |
| Callout | `callout: NodeId : text [pos=below]` (`above` / `below` / `below-left` / `below-right` / `left` / `right`). Optional `side=top\|bottom\|left\|right` sets where the connector leaves the callout box |
| Stacked column | `A -> { Upper / Lower } -> B` (edges attach to the stack mid-box; write a separate edge to each member to fan out) |
| Parallel edges | Repeat the same pair on separate lines; strokes offset and labels separate |
| Straight edges (flow) | `::: flow straight` (may combine with `wide`) sets the default shape for every edge in that flow |
| Step index | `::: flow steps` (may combine with `wide`) numbers each node with a muted counter |
| Fill leftover height | `::: flow fill` and `::: columns fill` (may combine with the other options) stretch those boxes to the height left on the slide |
| Lane map width | `::: flow spread` makes a plain multi-lane flow use the content width. The default stays a centred, shrink-wrapped group. `lane: … [align=end]` still moves one shorter lane |
| Big numbers | `::: columns figures` uses the same cards. The column heading is the figure (about 2.4em); the paragraph under it is the caption. The pair is centred in the card |

`A -> B -> C` on one line still chains. Nodes on separate lines stay unconnected until you write an arrow or a `link:` line. A bare `{#id}` in a chain refers to the existing node with that id (any lane); redefining `Name {#id}` when the id is already taken is still an error.

`::: flow wide` keeps the nodes on one row and centres that group with even gaps. Each box shares the row (`flow_node_max_width` defaults to `none`). Set `flow_node_max_width` to a length such as `240px` to cap the boxes and leave a side inset, or set it equal to `flow_node_min_width` to keep them content-sized in width too. That wide row grows toward `flow_preferred_height` (default `60%` of the slide content box) and the panel stays that tall. A plain flow stays content height. `flow_preferred_height: none` keeps content height, with a floor of `flow_node_min_height` (default `96px`). `flow_fill_height: fill`, or `::: flow fill` on one diagram, stretches boxes to the height left under the title. A node beside a `{ A / B }` stack stays as wide as its label; the stack uses the rest of the row. The title stays at the top. A key message directly under the title stays with it, and the blocks under that heading are centred in the leftover space. A trailing `::: question` stays on the bottom, with the leftover space split under the heading and above the question. A flow that contains a `callout:` stays content-height even then, so the note stays on the slide. `::: columns fill` asks column cards to take the leftover height; they already have a `column_min_height` floor (default `160px`). Lists in a column keep a `1.4em` indent (`.column ul` / `.column ol`) even when the deck style sets `ul { padding: 0 }`.

A deck style must not set `.flow-row { justify-content: space-between }` — or the same declaration on `.flow.flow-wide .flow-row`. That rule cancels this centring and pins the first and last box to the edges. Remove it when adopting these defaults. Do not add it to make the boxes larger; the default already shares the row.

A row that contains a `.flow-stack` keeps at least 72px between the stack and the neighbouring node so a fork trunk and its arrowheads fit. The boxes inside the stack are separated by `flow_stack_gap` (default `32px`). Separate edges into each stack member share that trunk. `A -> { A / B }` is still one arrow into the middle of the stack.

A node caption (`Name | caption`, hook `.flow-node-caption`) is one block of text. `\n` breaks it into lines. It uses `font_size_flow_body` (default `18px`) and the body text colour, including when the box is tall. Badges and chips stay on `font_size_small`. Short bullets inside a flow node are not a syntax yet; use chips (`[[a, b]]`) or a `::: columns` card. Bullets in flow nodes are a follow-up.

A column heading (`.column-head`) is about `1.1em` of the body size so a short title stays on one line. A paragraph in a card sits under that heading. A list in a tall card is packed under that heading as well; the extra height stays below the items, and the line-height stays a normal reading size. `::: columns figures` is the same card row with a large heading for a plain figure (class `.columns.figures`). The figure and its caption are centred in the card.

`**Key Message:**` is bold. `**emphasis**` inside the sentence is still inline Markdown.

### Lane layout

A plain (not `wide`) flow with lanes is as wide as its widest lane and is centred on the slide as one group. Lanes share the group's left edge, so boxes in the same position line up across lanes; a lane label sits on that edge above its first box. `lane: … [align=end]` (or `center`) moves one shorter lane, for example a single box that should sit under the last box of the lane above. `::: flow spread` (class `.flow-spread`) opts that group out of the shrink-wrap: the lanes span the content width and boxes in a row share it. An aligned lane inside that spread row stays as wide as its own boxes and is parked within the row, so `spread` and `align=end` can be used together without pushing the map past the content edge. The default stays centred and content-wide. A flow with a `{ A / B }` stack keeps the full row. Neighbouring boxes in a row keep at least 44px between them so a chain arrow has a shaft, not only a head. A lane joined to the lane above by a `link:` gets extra space above it for the vertical stroke and its label. Outside fill mode, lanes and rows do not shrink below their boxes; a diagram that is too tall makes the slide scale down instead of overlapping the next lane.

### Link routes and anchors

A vertical link (`bottom` → `top` or `top` → `bottom`) between two boxes whose widths overlap by at least 24px is one straight vertical stroke at a shared x, not a Z between the two centres. A label sits off the stroke and inside the flow: beside a vertical stroke, on the side that has room, or above or below a horizontal stroke. On a horizontal run it prefers the side that stays clear of other links and the arrowhead. It is not drawn across its own line or past the content edge. A callout sits far enough from its anchor (`flow_callout_gap`, at least the arrowhead plus a 16px shaft) that its connector reads as an arrow.

Cross-lane links and same-row edges that would pass through other nodes draw as orthogonal paths by default. Routing treats nodes, badges, callouts, and edge labels as obstacles, only in the rows or columns the path crosses. When several clear paths exist, the renderer picks a crossing-free one deterministically. Several edges that leave or enter the same node side use distinct ports spaced by `flow_port_gap` (default 12px) so arrowheads do not stack and trunks stay separate. Same-row U detours (fan-in or fan-out that bend above or below the row) widen that spacing to about an arrowhead width plus a gap, keep a final stub at least arrowhead length, and grow the flow's padding so nested trunks stay inside the flow box rather than crossing the slide title. Farther sources or targets take the outer trunk and farther port so routes nest without crossing.

Opt into straight (diagonal) strokes with `shape=straight` on a `link:` or chain destination, `::: flow straight`, or the style token `flow_edge_shape: straight`. Straight edges still use the same distributed ports, so fan-in into one target spreads as a fan of diagonals. When a straight segment would cross or run along another node’s border, the renderer falls back to an obstacle-avoiding orthogonal route (including a bend above or below a same-row chain) so trunks stay clear and distinct. Orthogonal remains the default.

Callout connectors with `side=` leave that side of the note box. If a simple L would run back through the callout itself (for example `pos=above side=left` when the note is centred over its anchor), the path steps outside the box, or falls back to the facing side (`bottom` for `above`, `top` for `below`). Facing and outside stubs keep a final segment long enough for the arrowhead.

| `route=` | Leaves source | Enters target | Corridor |
| --- | --- | --- | --- |
| `between` | bottom | top | Gap between the two rows (preferred for lane-to-lane); always orthogonal even when the source sits above the target’s width |
| `down` | bottom | top (gap) or bottom (around) | Prefers the between-lane gap; may detour below if the gap is blocked |
| `up` | top | bottom (gap) or top (around) | Prefers the between-lane gap above |
| `left` | left | left | Left of both boxes |
| `right` | right | right | Right of both boxes |
| `auto` | chosen | chosen | Scores gap, side, and around candidates; avoids node hits, shared trunks, and arrow crossings |

Multi-line edge labels sit entirely above or below their stroke (anchored by the label box) and widen the gap between same-row nodes when needed.

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

- `Source: …` or `出典:…` / `出典：…` on its own line moves into the footer with class `.source`. The `Source:` / `出典：` prefix is stripped from the line body; the visible prefix comes from `label_source` (see Labels)
- Or `::: source` … `:::` for a longer note (also gets `label_source` when non-empty)
- Page numbers render automatically as `n / total` with class `.page-number`
- `page_number_placement` (`bottom-right` default, also `bottom-left`, `bottom-center`) positions the page mark independently of the source footer

## Labels

Style tokens `label_question`, `label_key_message`, and `label_source` set the visible label text. When omitted, defaults follow `lang`:

| `lang` | Question | Key Message | Source |
| --- | --- | --- | --- |
| `ja` (and `ja-*`) | 議論の問い | キーメッセージ | 出典： |
| other | Question | Key Message | Source: |

Set `label_source: ""` to hide the footer source prefix (the pre-`label_source` look, where only the stripped body text appeared).

`question_label_placement` is `inline` by default (label in the first paragraph) or `block` (label on its own line above the body).

## Commands

```bash
uv run md-deck check examples/sample.md
uv run md-deck check path/to/slides.md --style path/to/style.md
uv run md-deck build examples/sample.md -o out/sample.pdf
```
