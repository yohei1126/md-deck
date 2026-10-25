# Stable styling hooks

md-deck emits a fixed set of classes and data attributes so deck style CSS can theme slides without `#slide-N` or `:nth-child()` selectors. Treat this list as the styling API: names here stay stable across releases unless a breaking change is called out in the GitHub Release notes or PR.

The generator still ships **no visual theme**. Hooks are layout landmarks only. Colours, type, radii, and chrome belong in the deck's style Markdown (tokens and `css` fences).

## Slide shell

| Hook | Where | Notes |
| --- | --- | --- |
| `.slide` | `<section>` | One per slide |
| `.slide[data-cover="true"]` | same | Cover slide: the first slide, or any slide whose H1 has class `cover`. Omitted when the first slide uses `.no-cover` and does not also use `.cover`. Base CSS centres the slide |
| `.cover-meta` | Paragraph under the cover `h1` | Front matter `subtitle` and `date`, joined with ` · `. Children: `.cover-sub`, `.cover-date` |
| `.slide[data-index]` | same | 1-based index (`data-index="3"`) |
| `.slide[data-slide]` | same | Same index (alias kept for older CSS) |
| `#slide-N` | same | Default `id` when the title has no `{#id}` |
| Author `id` / classes | same | From `# Title {#id .class}` (`attr_list`) |

Example:

```markdown
# Routing map {#routing .path-diagram}
```

becomes `<section class="slide path-diagram" id="routing" data-index="…">`.

## Content landmarks

| Hook | Element | Source |
| --- | --- | --- |
| `.title` | First `h1` | Always added (merged with any `attr_list` classes). A `\n` in the H1 source is a `<br>` inside this element. Titles use `text-wrap: balance` when they wrap without a `<br>` |
| `.key-message` | Key Message box | `**Key Message:** …` |
| `.key-message .label` | Label span | Text from `label_key_message` or `lang` default |
| `.question` | Discussion box | `::: question` |
| `.question.question-label-inline` | same | Default: label sits in the first paragraph |
| `.question.question-label-block` | same | When `question_label_placement: block` |
| `.question .label` | Label span | Text from `label_question` or `lang` default |
| `.columns` | Column row | `::: columns` |
| `.columns.plain` / `.columns.panel` / `.columns.fill` | same | Block options. `fill` asks the row to use leftover slide height |
| `.column` | One column | Split by `+++` |
| `.column-head` | First heading in a column | First `h2`–`h6` in that column |
| `.source` | Footer source | `Source:` / `出典:` line or `::: source` |
| `.source .label` | Source prefix | Text from `label_source` or `lang` default (omitted when `label_source` is empty). Weight / gap from `--source-label-weight` / `--source-label-gap` |
| `.page-number` | Footer page mark | Auto `n / total` |
| `.page-number[data-placement]` | same | `bottom-right` (default), `bottom-left`, or `bottom-center` from `page_number_placement` |
| `.slide-footer` | Footer wrapper | Layout only; source stays left, page number placement is separate |
| `.slide-footer[data-page-number-placement]` | same | Mirrors the page-number token |

## Tables

| Hook | Element | Source |
| --- | --- | --- |
| `table` | Table | Markdown table; font size from `--font-size-table` |
| `th` | Header cell | Header row |
| `th[scope=row]` | Row header | Empty first header cell promotes the first body column |

```markdown
|  | Plan A | Plan B |
| --- | --- | --- |
| Timing | before | after |
```

## Flow diagrams

| Hook | Element | Source |
| --- | --- | --- |
| `.flow` | Flow root | `::: flow`. A wide row with no stack grows toward `--flow-preferred-height` (default `60%`). `flow_fill_height: fill` or `.flow-fill` takes the leftover height |
| `.flow.flow-wide` | same | `::: flow wide` (one centred row, even gaps, boxes grow up to `--flow-node-max-width`) |
| `.flow.flow-steps` | same | `::: flow steps` (muted step index on `.flow-node-title::before`) |
| `.flow.flow-straight` | same | `::: flow straight` (default edge shape) |
| `.flow.flow-fill` | same | `::: flow fill` (stretch this diagram to the leftover slide height) |
| `.flow-lanes` | Lane stack | Always present (single-lane flows included) |
| `.lane` | One lane | `lane: Label` or the implicit single lane |
| `.lane[data-lane]` | same | 0-based lane index |
| `.lane-label` | Lane title | Text after `lane:` |
| `.flow-row` | Node row inside a lane | Always present inside each `.lane` |
| `.flow-stack` | Vertical stack | `{ A / B }` in a chain. Gap is `--flow-stack-gap` (default `32px`) |
| `.flow-node` | Node box | Each node |
| `.flow-node[data-node]` | same | Node key (`{#id}` when set, else title; chips-only nodes use `[[a, b]]`) |
| `.flow-node[data-id]` | same | Present when `Name {#id}` was set |
| `.flow-node[data-kind]` | same | `actor`, `system`, `doc`, `muted`, or `highlight` |
| `.flow-node-actor` (etc.) | same | Class mirror of `data-kind` |
| `.flow-node-title` | Title span | Primary label (omitted for chips-only nodes) |
| `.flow-node-caption` | Caption span | `Name \| caption` |
| `.flow-node-badge` | Badge span | `Name {badge}` |
| `.flow-chips` / `.flow-chip` | Chip tags | `Name [[chip1, chip2]]` or chips-only `[[a, b]]` |
| `div.flow-callout` | Note box | `callout: NodeId : text [pos=below]` |
| `div.flow-callout[data-anchor]` / `[data-pos]` | same | Anchor key and position (`below-left` / `below-right` included) |
| `div.flow-callout[data-side]` | same | Optional connector exit side (`top` / `bottom` / `left` / `right`) |
| `path.flow-callout` | Callout connector (SVG) | Same hook name on the dashed connector path |
| `.flow-edge` | Edge descriptor | Hidden; read by `deck.js` |
| `.flow-edge[data-shape]` | same | `orthogonal` (default) or `straight` |
| `.flow-edge[data-from-attach]` / `[data-to-attach]` | same | `stack` when the chain endpoint was a `{ A / B }` column |
| `.flow-edge-cross` | Cross-lane edge | From `link: A => B : label` |
| `.flow-svg` | SVG overlay | Drawn at render time |

### SVG arrow and label API (stable)

Every drawn arrow path and label text carries these hooks. Style CSS may target them; they are part of the public API.

| Hook | Element | Notes |
| --- | --- | --- |
| `.flow-arrow` | SVG `<path>` | Every arrow |
| `.flow-arrow-dashed` | SVG `<path>` | Dashed stroke |
| `.flow-link` | SVG `<path>` | Cross-lane `link:` and callout connectors |
| `.flow-callout-arrow` | SVG `<path>` | Callout connector (also carries `.flow-link` and `.flow-callout`) |
| `.flow-label` | SVG `<text>` | Arrow label (`.flow-edge-label` kept as an alias) |
| `[data-from]` / `[data-to]` | path and text | Endpoint node keys |
| `[data-kind]` | path and text | `solid`, `dashed`, `bidirectional`, or `link` |
| `[data-shape]` | path | `orthogonal` or `straight` when set on the edge |

Theme node kinds in the style file:

```css
.flow-node[data-kind="doc"] {
  background: var(--color-highlight-bg);
  border-color: var(--color-highlight);
}

.flow-node[data-kind="system"] {
  border-style: double;
}

.flow-svg path.flow-link {
  stroke-width: 2.5;
}

.flow-svg text.flow-label {
  font-weight: 700;
}

.flow-chip {
  border-color: var(--color-highlight);
}
```

## Tokens as CSS variables

Every style token is emitted on `:root` (see [STYLE_GUIDE.md](STYLE_GUIDE.md)). Prefer variables such as `var(--color-top-bar)`, `var(--font-size-table)`, and `var(--label-question)` over hard-coded values when the token exists.

## What not to rely on

- `#slide-1 .flow-node:nth-of-type(3)` and similar positional selectors
- Ordering of anonymous wrappers around flow lanes
- Exact SVG path geometry (orthogonal routes may gain clearance; classes and `data-*` hooks above stay)

If a look needs a new landmark, open an issue or PR to add a named hook rather than encoding slide index into CSS.
