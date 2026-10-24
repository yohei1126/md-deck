# Stable styling hooks

md-deck emits a fixed set of classes and data attributes so deck style CSS can theme slides without `#slide-N` or `:nth-child()` selectors. Treat this list as the styling API: names here stay stable across releases unless a breaking change is called out in the changelog or PR.

The generator still ships **no visual theme**. Hooks are layout landmarks only. Colours, type, radii, and chrome belong in the deck's style Markdown (tokens and `css` fences).

## Slide shell

| Hook | Where | Notes |
| --- | --- | --- |
| `.slide` | `<section>` | One per slide |
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
| `.title` | First `h1` | Always added (merged with any `attr_list` classes) |
| `.key-message` | Key Message box | `**Key Message:** …` |
| `.key-message .label` | Label span | Text from `label_key_message` or `lang` default |
| `.question` | Discussion box | `::: question` |
| `.question .label` | Label span | Text from `label_question` or `lang` default |
| `.columns` | Column row | `::: columns` |
| `.columns.plain` / `.columns.panel` | same | Block options |
| `.column` | One column | Split by `+++` |
| `.column-head` | First heading in a column | First `h2`–`h6` in that column |
| `.source` | Footer source | `Source:` / `出典:` line or `::: source` |
| `.page-number` | Footer page mark | Auto `n / total` |
| `.slide-footer` | Footer wrapper | Layout only |

## Flow diagrams

| Hook | Element | Source |
| --- | --- | --- |
| `.flow` | Flow root | `::: flow` |
| `.flow.flow-wide` | same | `::: flow wide` |
| `.flow-lanes` | Lane stack | Present when there is more than one lane or a `lane:` label |
| `.lane` | One lane | `lane: Label` (or the implicit single lane) |
| `.lane[data-lane]` | same | 0-based lane index |
| `.lane-label` | Lane title | Text after `lane:` |
| `.flow-row` | Node row inside a lane | Multi-lane layouts |
| `.flow-node` | Node box | Each node |
| `.flow-node[data-node]` | same | Node key (title text) for links |
| `.flow-node[data-kind]` | same | `actor`, `system`, `doc`, `muted`, or `highlight` |
| `.flow-node-actor` (etc.) | same | Class mirror of `data-kind` |
| `.flow-node-title` | Title span | Primary label |
| `.flow-node-caption` | Caption span | `Name \| caption` |
| `.flow-node-badge` | Badge span | `Name {badge}` |
| `.flow-edge` | Edge descriptor | Hidden; `deck.js` reads `data-from` / `data-to` / `data-style` / `data-label` |
| `.flow-edge-cross` | Cross-lane edge | From `link: A => B : label` |
| `.flow-svg` | SVG overlay | Drawn at render time |
| `.flow-edge-label` | SVG `<text>` | Arrow label |

Theme node kinds in the style file:

```css
.flow-node[data-kind="doc"] {
  background: var(--color-highlight-bg);
  border-color: var(--color-highlight);
}

.flow-node[data-kind="system"] {
  border-style: double;
}

.flow-node[data-kind="muted"] {
  color: var(--color-muted);
}
```

## Tokens as CSS variables

Every style token is emitted on `:root` (see [STYLE_GUIDE.md](STYLE_GUIDE.md)). Prefer variables such as `var(--color-top-bar)` and `var(--label-question)` over hard-coded values when the token exists.

## What not to rely on

- `#slide-1 .flow-node:nth-of-type(3)` and similar positional selectors
- Ordering of anonymous wrappers around flow lanes
- Exact SVG path shape (geometry may change; classes and data attributes stay)

If a look needs a new landmark, open an issue or PR to add a named hook rather than encoding slide index into CSS.
