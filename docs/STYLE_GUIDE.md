# Style Markdown and slide conventions

md-deck renders decks. The default palette is plain black on white. `theme: dark-blue` in the style file is an opt-in role palette. Each deck repository owns two Markdown files: slide content and a style file. The style file is both the human-readable style guide and the machine-readable tokens.

The **input contract** (required front matter, schemas, asset paths, and `md-deck check` rules) is in [INPUT_FORMAT.md](INPUT_FORMAT.md). HTML hooks for style CSS are in [HOOKS.md](HOOKS.md). This page lists tokens and authoring conventions.

## Style file shape

A style file is Markdown with:

1. YAML front matter: theme tokens
2. Prose: guidance for authors (ignored by the generator)
3. Optional fenced `css` blocks: extra rules appended after the token CSS

Pass the file with `--style path/to/deck_style.md`, or set `style:` in the slides front matter. The CLI flag overrides front matter. If neither resolves to a file, the check fails.

`examples/deck_style.md` is a plain black-on-white sample that lists tokens. Copy it into a deck repo and change the values; do not treat it as a product look. [`examples/deck_style_dark_blue.md`](../examples/deck_style_dark_blue.md) is the opt-in palette. The sample builds stay on the plain file.

## Required vs optional tokens

Required (check fails if missing):

- `font_family`, `font_size_body`
- `color_background`, `color_text`, `color_title`, unless `theme: dark-blue` (that theme supplies them)

`theme` is `plain` (default) or `dark-blue`. It is not a CSS variable. `dark-blue` fills omitted colour tokens. A colour token you set overrides that role. When to use a role is [visual-color/SKILL.md](https://github.com/yohei1126/agent-skills/blob/main/visual-color/SKILL.md). When to draw a diagram is [visual-diagram/SKILL.md](https://github.com/yohei1126/agent-skills/blob/main/visual-diagram/SKILL.md). Deck authoring is [md-deck/SKILL.md](https://github.com/yohei1126/agent-skills/blob/main/md-deck/SKILL.md). This page does not copy those skills.

Optional tokens use the plain defaults in the table below when omitted. Unknown names fail the check. See [`schemas/style.schema.json`](../schemas/style.schema.json).

## Token schema

Bare numbers for lengths become `px`, except `line_height`, `font_weight_title`, `font_weight_body`, and `source_label_weight`, which stay unitless. Strings are emitted as written (so you can pass `"1.5rem"` or a font stack). Colours must be valid CSS colour strings (`#rgb`, `#rrggbb`, `rgb()`, `hsl()`, or a named colour).

For radii, borders, and paddings in `ZERO_OR_NONE` scope, `0` and `none` are allowed (for example `card_radius: 0`, `border_width: none`).

Per-side page padding: set `page_padding_top` / `_right` / `_bottom` / `_left`. If a side is omitted but `page_padding` is set, that side inherits `page_padding`.

Label tokens become both HTML label text (when set) and quoted CSS variables for `content: var(--label-question)`.

| Token | CSS variable | Plain default | Required | Role |
| --- | --- | --- | --- | --- |
| `page_width` | `--page-width` | `1280px` | no | Slide width |
| `page_height` | `--page-height` | `720px` | no | Slide height |
| `theme` | — | `plain` | no | `plain` or `dark-blue`. Not emitted as CSS. `dark-blue` fills omitted colour tokens |
| `color_background` | `--color-background` | `#ffffff` | **yes** | Page background. Supplied by `theme: dark-blue` when omitted |
| `color_text` | `--color-text` | `#000000` | **yes** | Body text |
| `color_muted` | `--color-muted` | `#444444` | no | Secondary text (`.muted`, captions) |
| `color_gray` | `--color-gray` | `#444444` | no | Gray accent (alias-style token for decks that distinguish gray from muted) |
| `color_border` | `--color-border` | `#cccccc` | no | Generic border token |
| `color_title` | `--color-title` | `#000000` | **yes** | `h1`–`h3` / accent |
| `color_top_bar` | `--color-top-bar` | `#000000` | no | Top bar / rule colour for style CSS |
| `color_accent_2` | `--color-accent-2` | `#666666` | no | Secondary accent. Eyebrows use it. `dark-blue` sets `#1A6B7A` |
| `color_highlight` | `--color-highlight` | `#000000` | no | Highlight stroke / text |
| `color_highlight_bg` | `--color-highlight-bg` | `#f5f5f5` | no | Highlight fill |
| `color_key_message_bg` | `--color-key-message-bg` | `#f5f5f5` | no | Key Message box fill |
| `color_key_message_text` | `--color-key-message-text` | `#000000` | no | Key Message text |
| `color_key_message_border` | `--color-key-message-border` | `#cccccc` | no | Key Message border |
| `color_question_bg` | `--color-question-bg` | `#f5f5f5` | no | Question box fill |
| `color_question_text` | `--color-question-text` | `#000000` | no | Question text |
| `color_question_border` | `--color-question-border` | `#cccccc` | no | Question border |
| `color_card_bg` | `--color-card-bg` | `#ffffff` | no | Column card fill |
| `color_card_border` | `--color-card-border` | `#cccccc` | no | Column card border |
| `color_flow_node_bg` | `--color-flow-node-bg` | `#ffffff` | no | Flow node fill |
| `color_flow_node_border` | `--color-flow-node-border` | `#000000` | no | Flow node border |
| `color_flow_arrow` | `--color-flow-arrow` | `#000000` | no | Flow arrow stroke |
| `color_edge_gap` | `--color-edge-gap` | `#000000` | no | Dashed gap stroke and label. `dark-blue` sets the accent `#F7581D` |
| `color_table_header_bg` | `--color-table-header-bg` | `#f0f0f0` | no | Table header fill |
| `color_table_border` | `--color-table-border` | `#cccccc` | no | Table cell borders |
| `font_family` | `--font-family` | `sans-serif` | **yes** | Font stack |
| `font_size_body` | `--font-size-body` | `22px` | **yes** | Body size |
| `font_size_title` | `--font-size-title` | `36px` | no | Title size |
| `font_size_key_message` | `--font-size-key-message` | `20px` | no | Key Message size |
| `font_size_question` | `--font-size-question` | `18px` | no | Question size |
| `font_size_small` | `--font-size-small` | `16px` | no | Footer, badges, chips |
| `font_size_flow_body` | `--font-size-flow-body` | `18px` | no | Flow-node caption (`.flow-node-caption`). Body colour, not muted |
| `font_size_table` | `--font-size-table` | `font_size_small` | no | Table body size (falls back to `font_size_small` when omitted) |
| `font_weight_title` | `--font-weight-title` | `700` | no | Titles and labels |
| `font_weight_body` | `--font-weight-body` | `400` | no | Body weight |
| `line_height` | `--line-height` | `1.45` | no | Body line height |
| `page_padding` | `--page-padding` | `48px` | no | Default inset; fills omitted sides |
| `page_padding_top` | `--page-padding-top` | `48px` | no | Top inset |
| `page_padding_right` | `--page-padding-right` | `48px` | no | Right inset |
| `page_padding_bottom` | `--page-padding-bottom` | `48px` | no | Bottom inset |
| `page_padding_left` | `--page-padding-left` | `48px` | no | Left inset |
| `footer_inset_bottom` | `--footer-inset-bottom` | `0.6em` | no | Distance from the page bottom edge to `.slide-footer` (negative allowed) |
| `footer_inset_right` | `--footer-inset-right` | `0px` | no | Added to `page_padding_right` for the footer’s right edge; use a negative value (for example `-20px`) to sit closer to the page edge than the content padding |
| `gap` | `--gap` | `16px` | no | Flex gaps |
| `card_radius` | `--card-radius` | `8px` | no | Column / flow corner radius (`0` / `none` ok) |
| `card_padding` | `--card-padding` | `16px` | no | Inner padding for boxes |
| `key_message_radius` | `--key-message-radius` | `8px` | no | Key Message radius |
| `question_radius` | `--question-radius` | `8px` | no | Question radius |
| `border_width` | `--border-width` | `1px` | no | Default border width (`0` / `none` ok). `theme: dark-blue` sets `2px` when this token is omitted |
| `flow_node_min_width` | `--flow-node-min-width` | `120px` | no | Minimum flow node width (`0` / `none` ok) |
| `flow_node_max_width` | `--flow-node-max-width` | `none` | no | Cap for boxes in a wide row or beside a stack. `none` (the default) lets those boxes share the row. A length such as `240px` keeps a centred inset |
| `flow_node_min_height` | `--flow-node-min-height` | `96px` | no | Floor on a flow node (`0` / `none` sizes to the label). A wide row still grows toward `flow_preferred_height` |
| `flow_preferred_height` | `--flow-preferred-height` | `60%` | no | A `::: flow wide` row with no stack grows toward this share of the slide content box. `none` keeps content height. A length such as `220px` is a fixed cap. `flow_fill_height: fill` ignores it |
| `flow_stack_gap` | `--flow-stack-gap` | `32px` | no | Vertical gap between boxes inside a `{ A / B }` stack (`0` / `none` ok) |
| `flow_fill_height` | `--flow-fill-height` | `none` | no | `none` uses `flow_preferred_height` for a wide row and content height otherwise. `fill` stretches every flow to the leftover slide height |
| `column_min_height` | `--column-min-height` | `160px` | no | Floor on a column card (`0` / `none` sizes to the copy). The row stays content height unless the block is `::: columns fill` |
| `flow_node_padding` | `--flow-node-padding` | `12px` | no | Flow node padding |
| `flow_callout_gap` | `--flow-callout-gap` | `12px` | no | Gap between a callout box and its anchor node |
| `flow_port_gap` | `--flow-port-gap` | `12px` | no | Spacing between fan-in / fan-out edge ports on one node side |
| `flow_edge_shape` | `--flow-edge-shape` | `orthogonal` | no | Default edge shape: `orthogonal` or `straight` (overridden by `::: flow straight` or per-edge `shape=`) |
| `label_question` | `--label-question` | from `lang` | no | Question label string |
| `label_key_message` | `--label-key-message` | from `lang` | no | Key Message label string |
| `label_source` | `--label-source` | from `lang` | no | Footer source prefix (`Source:` / `出典：`). Empty string hides it |
| `source_label_weight` | `--source-label-weight` | `600` | no | Font weight for `.source .label` |
| `source_label_gap` | `--source-label-gap` | `0.15em` | no | Gap after `.source .label` (`margin-inline-end`; `0` removes it) |
| `question_label_placement` | `--question-label-placement` | `inline` | no | `inline` (label in first paragraph) or `block` |
| `page_number_placement` | `--page-number-placement` | `bottom-right` | no | `bottom-right`, `bottom-left`, or `bottom-center` (independent of `.source`) |

When `label_*` tokens are omitted, defaults follow the slides `lang` (`ja` → 議論の問い / キーメッセージ / 出典：; otherwise Question / Key Message / Source:). See [INPUT_FORMAT.md](INPUT_FORMAT.md).

## Optional CSS fence

```css
.slide::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  height: 6px;
  background: var(--color-top-bar);
}

.flow-node[data-kind="doc"] {
  background: var(--color-highlight-bg);
  border-color: var(--color-highlight);
}
```

Rules from every `css` fence in the style file are appended after the generated `:root` block. `--css file.css` on the CLI appends still later. Prefer [HOOKS.md](HOOKS.md) selectors over slide-index hacks.

## Slide Markdown conventions

| Construct | Syntax | Check rule |
| --- | --- | --- |
| Slide break | a line that is exactly `---` | no empty slide from a trailing `---` |
| Title | exactly one `# Heading` per slide; optional `{#id .class}` | missing / extra H1 fail |
| Key Message | at most one `**Key Message:** …` line | extras fail |
| Question box | `::: question` … `:::` | non-empty; known kinds only |
| Source | `Source:` / `出典:` line or `::: source` | empty source block fails |
| Flow | `::: flow` / `wide` / `straight` / `steps` / `fill` with arrows, lanes, links, callouts, stacks, chips, `{#id}`, `shape=` | ≥2 nodes; known options/kinds/routes/shapes |
| Columns | `::: columns` / `plain` / `panel` / `fill`, split by `+++`; may nest one `::: flow` | ≥2 non-empty columns; other nesting forbidden |
| Hard break | trailing `\`; `\n` in flow labels/badges/titles and in an H1 | also: newlines inside question/source |
| Table / lists | normal Markdown; empty corner → row headers | consistent columns; list class without forced `<p>` |
| Code fence | ` ``` ` … ` ``` ` | must close |
| HTML | not used by default | fails unless `--allow-html` |

Slides front matter must include `title`, `version`, `date`, `lang`, and `style` (see [INPUT_FORMAT.md](INPUT_FORMAT.md)).

## Overflow

After layout, each slide scales down in 2% steps to 80% if content overflows. If it still overflows, the build fails and names the slide numbers. Shorten the copy or adjust tokens (font sizes, padding) in the style file.

## Visual policy and cover titles

Slide materials aim at a NotebookLM-like reading ease: tidy colour, structured information, and a clear diagram bone (boxes, arrows, branches). Flashy decoration is out of scope. The pipeline limits, the phased plan, and the cover-title rules are in [VISUAL_POLICY.md](VISUAL_POLICY.md). Before/after recipes for a 2-box compare, a branch, and a 3-step row are in [DIAGRAMS.md](DIAGRAMS.md) and [`examples/diagram_patterns.md`](../examples/diagram_patterns.md).

Cover titles (the first slide, or an H1 with `{.cover}`):

- Do not leave a wrap in the middle of a phrase. Put `\n` in the H1 at a phrase boundary (`# First phrase\nSecond phrase`).
- When a title uses more than one line, keep the lines similar in length.
- `md-deck check` enforces that rule for cover titles. A later line that starts with a loose particle is a warning and does not fail the build. `text-wrap: balance` evens a Latin title that still wraps once on its own.
- The cover slide is centred. `subtitle` and `date` from front matter render under the title. An optional frame and a larger title are deck CSS, not a built-in chrome; the snippet is in [VISUAL_POLICY.md](VISUAL_POLICY.md).
- `::: flow wide` centres the row and the boxes share its width (`flow_node_max_width` defaults to `none`). That wide row grows toward `flow_preferred_height` (default `60%` of the slide content box) and the panel stays that tall. A plain flow stays content height. `none` keeps content height. `flow_fill_height: fill` or `::: flow fill` stretches boxes to the leftover slide height. The title stays at the top; blocks under it (and under a key message that follows the title) are centred in what remains. A trailing question stays on the bottom, and that leftover space splits under the heading and above the question. `steps` adds a muted index. A fork keeps 72px beside the stack and `flow_stack_gap` (`32px`) between the stacked boxes. The node beside the stack stays as wide as its label; the stack uses the rest of the row. A list in a stretched column stays packed under the heading. A wide step box keeps its title and caption at the top. `::: columns figures` centres the figure in the card.
- A deck style must not set `.flow-row { justify-content: space-between }` (the same declaration on `.flow.flow-wide .flow-row` is the same problem). It cancels the centred row. Remove it when adopting these defaults.
- Confirm the cover in a PNG: `md-deck build slides.md -o out.pdf --png out/png`.

`{.no-cover}` on the first H1 opts that slide out of the cover check. See [VISUAL_POLICY.md](VISUAL_POLICY.md) for the thresholds.
