# Visual policy

md-deck should produce slide materials that are as easy to read as a NotebookLM slide, without becoming a flashy deck. Colour stays quiet. Information is structured. The bone of a diagram — boxes, arrows, and branches — is obvious.

This page is the generator-side record of that policy: what the HTML/CSS → PDF path can draw today, what it cannot, which approach to take, and how cover titles may break. Recipes and before/after markup are in [DIAGRAMS.md](DIAGRAMS.md). Tokens stay in [STYLE_GUIDE.md](STYLE_GUIDE.md). The authoring skill in [yohei1126/agent-skills](https://github.com/yohei1126/agent-skills/blob/main/md-deck/SKILL.md) is updated separately; do not copy it into this repo. When to use a colour, for decks and for article covers and diagrams, is a separate shared color skill in that same repository. This page does not repeat it.

## Policy

- One idea per slide. The Key Message is one sentence.
- A diagram label is a name, not a sentence. Aim for about four English words or about twelve CJK characters. The checker does not enforce that budget yet.
- Compare two things with `::: columns`. Use `panel` when the box border should show (the default `.column` border already does; `panel` is the hook). Use `plain` only when the border should disappear. Do not draw a comparison as an arrow.
- Branch with one box and one arrow per outcome. Do not put "A or B" inside a single node.
- Show a short procedure as one horizontal row: `::: flow wide` (centred, even gaps). Add `steps` for a muted index on each box.
- Colours come from style tokens: background, text, one quiet accent, a muted secondary. No gradients, drop shadows, stickers, or icon collages in the style CSS.
- Node kinds (`actor`, `system`, `doc`, `muted`, `highlight`) are hooks. Base CSS does not paint them differently. A deck may tint `muted` / `highlight` with the existing tokens. It should not invent a bright per-kind palette.
- Photos, logos, and maps may be images. Boxes-and-arrows should not be images.
- Shrink-to-fit (down to 80%) is a last resort. Cut the copy before relying on it.

`examples/` in this repo stays generic. Customer and proposal copy belongs in the deck repository.

## Colour

The sample style stays plain: black on white. In a deck style file, `theme: dark-blue` fills any colour token you omit. A colour token you set still wins. The values are CSS variables on the slide background, titles, body text, flow-node borders and fills, arrows, column cards, and question blocks. Copy [`examples/deck_style_dark_blue.md`](../examples/deck_style_dark_blue.md). Token names are in [STYLE_GUIDE.md](STYLE_GUIDE.md).

`dark-blue` is one 60/30/10 role set, not a product brand. Ground `#EDE8E4` (the sample's sub colour, not its pure white), text `#333333`, navy `#073365` for titles, node borders, and arrows, accent `#F7581D` for callouts and the question border. Card and key-message fills use a light navy tint (`#E3EAF2`). Node fill stays off-white (`#F4F0EC`).

## 参考

1. [プレゼンデザイン Dark blue](https://ppt.design4u.jp/theme-color-samples/) — HEX roles for that sample. The site closed in May 2026. [Wayback](https://web.archive.org/web/2024/https://ppt.design4u.jp/theme-color-samples/).
2. [Deckary: PowerPoint color schemes](https://deckary.com/blog/powerpoint-color-schemes) — navy, gray, and one accent, as 60-30-10. Navy `#003366` is close to `#073365`; this repo ships one palette.
3. [Cambridge slide accessibility](https://www.cctl.cam.ac.uk/slide-accessibility-guidance) — avoid a pure white ground; navy on off-white.
4. [デジタル庁 カラー](https://design.digital.go.jp/dads/foundations/color/) — colour as separate role tokens.
5. [ONS PowerPoint](https://service-manual.ons.gov.uk/brand-guidelines/application/creating-powerpoint-presentations) — a bright white ground is harder to read; their template uses a gray ground.

## What the pipeline can draw

The path is fixed:

1. Markdown is checked and turned into HTML (`::: flow`, `::: columns`, tables, lists, one H1, one Key Message).
2. Style tokens become CSS variables. Optional `css` fences and `--css` append after `base.css`.
3. Headless Chromium lays out the page. `deck.js` measures the flow DOM and draws SVG arrows.
4. Chromium prints a 16:9 PDF. If a slide still overflows after scaling to 80%, the build fails.

Stable classes are [HOOKS.md](HOOKS.md). Arrow path geometry is not stable; the classes and `data-*` hooks are.

| Piece | Today |
| --- | --- |
| Horizontal steps | `A -> B -> C`. `::: flow wide` keeps one centred row with even gaps. Boxes share that row (`flow_node_max_width` defaults to `none`) and grow toward `flow_preferred_height` (default `60%` of the slide). `steps` adds a muted index. Full leftover-height stretch is `flow_fill_height: fill` or `::: flow fill`. A length cap such as `240px` brings back a side inset |
| Two-up compare | `::: columns` / `panel` / `plain` / `fill`, split with `+++`. Cards have a `column_min_height` floor and already stretch with the row. A column heading stays near body size; a paragraph sits under it. `::: columns figures` is the same row with a large heading. A column may contain one nested `::: flow` |
| Branch | A `{ A / B }` stack plus a separate edge into each member. Those edges share a trunk and keep at least 72px before the stack so arrowheads do not sit in the corners. Same-row fan-out (no stack) is still routed as nested trunks |
| Lanes and cross-links | `lane:` and `link:` with `route=` (`between`, `down`, `up`, `left`, `right`, `auto`). A plain multi-lane flow is centred as one group. `::: flow spread` makes that group use the content width. `lane: … [align=end]` (or `center`) moves a shorter lane. A vertical link between boxes that overlap horizontally is one straight stroke. See [INPUT_FORMAT.md](INPUT_FORMAT.md) |
| Edge shapes | Orthogonal (default) or straight. Dashed, labelled, and bidirectional arrows |
| Node chrome | One rectangle. Caption, badge, chips, callout. Kinds are data attributes |
| Tables, lists, question, source, footer page number | Yes |
| Images | Relative paths that stay inside the slides directory |
| Title wrap | `text-wrap: balance` and `line-break: strict` on `.title`. Explicit `\n` in an H1 becomes `<br>` |
| Cover mark | First `<section>` gets `data-cover="true"`, as does any slide whose H1 has class `cover`. Base CSS centres that slide. Front matter `subtitle` and `date` render as `.cover-meta` under the title |

The cover is still a normal slide plus a quiet title-slide layout: the block is centred, the title is centred, and front matter `subtitle` and `date` (when set) sit on one muted line under the H1 (`.cover-meta`). `author` and `audience` are validated and are not drawn. Front matter `title` remains the PDF document title (`<title>`). A further line in the slide body is an ordinary paragraph, also centred.

md-deck does not ship a cover frame or an accent band. `theme: dark-blue` is an opt-in role palette, not a product brand. A reusable, token-only frame and a larger title — still no product colours — look like this in the deck style's `css` fence. Leave it out when the plain centred cover is enough. The same comment lives in [`examples/deck_style.md`](../examples/deck_style.md) and is not applied to the sample build.

```css
.slide[data-cover="true"] .slide-content {
  border: var(--border-width) solid var(--color-border);
  padding: 48px 64px;
}

.slide[data-cover="true"] .title {
  font-size: 48px;
}

.slide[data-cover="true"] .cover-meta {
  margin-top: 0.35em;
}
```

## Box size

Flow and column boxes used to shrink to their labels and sit in empty space. The defaults now give them a floor and, on a wide row or beside a stack, a width cap:

| Token | Default | Role |
| --- | --- | --- |
| `flow_node_min_width` | `120px` | Floor so a short label does not collapse the box |
| `flow_node_max_width` | `none` | No ceiling on a wide row or a stack row, so the boxes share the panel. A length (for example `240px`) caps them and leaves a centred inset |
| `flow_node_min_height` | `96px` | Floor on a flow node. `0` or `none` sizes strictly to the label. A wide row still grows toward `flow_preferred_height` |
| `flow_preferred_height` | `60%` | A `::: flow wide` row with no stack grows toward this share of the slide content box. `none` keeps content height. A length such as `220px` caps that grow. `flow_fill_height: fill` ignores the cap |
| `flow_fill_height` | `none` | `fill` stretches every flow box to the height left under the title. The default does not |
| `flow_stack_gap` | `32px` | Space between the boxes inside a `{ A / B }` stack. This is separate from the 72px trunk gap beside the stack |
| `column_min_height` | `160px` | Floor on every column card |

With the default `flow_node_max_width: none`, a wide row's boxes share the width of the panel and stay on even gaps. The row is still centred; there is simply no empty side band left to centre inside. Set a length on `flow_node_max_width` when a deck wants that band back. A `::: flow wide` row with no stack grows toward `flow_preferred_height` (default `60%` of the slide content box), and the panel stays that tall, so the boxes are not content-only and not stretched to the full leftover height. A plain flow stays content height. `flow_preferred_height: none` keeps content height. A node beside a stack stays as wide as its label; the stack uses the rest of the row. The title stays at the top of the slide. A key message directly under the title stays with it. The blocks under that heading are centred in the leftover space. A question that is the last block stays on the bottom, and the leftover space splits under the heading and above the question. Set `flow_fill_height: fill` to stretch every flow to the height left under the title, or mark one diagram with `::: flow fill` (class `.flow-fill`). A flow that contains a callout does not stretch: the note is drawn outside the node, and stretching that node to the bottom of the slide would push the note off the page. `::: columns fill` asks column cards to take the height still free; they already have a `column_min_height` floor.

Lists inside a column keep `padding-inline-start: 1.4em` from `.column ul` / `.column ol`. That selector is more specific than a deck rule of `ul { padding: 0 }`, so the markers stay indented in a panel. When the card is taller than the list, the items are spaced through the card instead of packing under the heading.

A deck style must not set `.flow-row { justify-content: space-between }` (or the same declaration on `.flow.flow-wide .flow-row`). It cancels the centred row and pins the end boxes to the edges. Remove that declaration when adopting these defaults. It is not the way to enlarge the boxes.

A plain flow with lanes is centred as one group, as wide as its widest lane, and a lane label sits on that left edge. `::: flow spread` (`.flow-spread`) opts a multi-lane map into the content width; the default stays shrink-wrapped. `lane: … [align=end]` (or `center`) moves one shorter lane. Neighbouring boxes keep at least 44px between them so a chain arrow has a shaft. A vertical link between overlapping boxes is one straight stroke, with the label beside the line. Outside fill mode, lanes and rows do not shrink below their boxes; a diagram that is too tall scales the slide down instead of overlapping the next lane. Markup is in [INPUT_FORMAT.md](INPUT_FORMAT.md).

A caption on a flow node stays one text block (`Name | caption`, with `\n` for extra lines). It uses `font_size_flow_body` (default `18px`) and the body colour, so a tall box does not leave the sentence in small grey type. Chips (`[[a, b]]`) stay on the small size. A short bullet list inside a flow node is not supported yet; that remains a follow-up. Use a column card when the text is a list. A card heading is about `1.1em` of the body, and a paragraph in the card sits under that heading. `::: columns figures` is the big-number row on the same cards. A Key Message is bold; `**emphasis**` in the sentence stays inline Markdown.

## What it cannot draw

These are the current ceilings. They are properties of this generator, not of HTML in the abstract.

- Curved connectors, custom arrowheads per edge, and any stroke that is not orthogonal or straight.
- Non-rectangle nodes: diamond, circle, chevron, icon, illustration.
- A junction dot. Fan-out is box-to-box. `A -> { B / C }` attaches **one** arrow to the middle of the stack. A fork needs a separate edge to each member (see [DIAGRAMS.md](DIAGRAMS.md)).
- Phrase segmentation. There is no BudouX (or similar) step. A CJK title wraps between characters unless the author writes `\n`.
- An enforced copy budget. Density fails the build only when the slide still overflows at 80% scale. A slide full of sentences can be valid and still hard to read.
- Raw HTML or SVG in the slides file (`--allow-html` is off by default), so a NotebookLM-style drawing cannot be pasted in.
- Author-placed arrow coordinates. `deck.js` chooses a crossing-free orthogonal route. Exact `d` attributes are not an API.
- Nested blocks other than one `::: flow` inside `::: columns`.
- A built-in icon set, gradient, shadow, cover frame, or brand band. A deck style file could add them. This policy says not to ship them from the generator. A token-only cover frame is an optional snippet, not a default.
- A bullet list inside a flow node. The caption is text (`Name | caption`, `\n` for lines) and chips are `[[a, b]]`. A list belongs in a column. Bullets in flow nodes are a follow-up.

## Bottleneck

The HTML/CSS → PDF path can already draw the bone: rectangles, arrows, a two-column compare, a fork, a three-step row. It does not match a NotebookLM slide by adding decoration. The gap is unnamed recipes, sentence-length labels, a single rectangle chrome, and CJK titles that wrap mid-phrase. About half of the visual gap on a dense slide is the length of the copy.

## Recommended approach

**Stay on HTML nodes plus SVG arrows.** Do not move diagrams onto pasted images or hand-authored SVG. Write the frequent patterns as Markdown recipes on `::: columns` and `::: flow`. Add a new drawing primitive only when a recipe cannot stay readable.

| Option | Role |
| --- | --- |
| Markdown recipes (this phase) | Default. Compare, branch, and 3-step rows are fixed templates in [DIAGRAMS.md](DIAGRAMS.md) and [`examples/diagram_patterns.md`](../examples/diagram_patterns.md). They use syntax the checker already accepts |
| SVG components inside the generator | Later, and only for a bone the recipes cannot draw (a junction dot, a step index). Still measured by `deck.js`, still themed by tokens |
| Image or hand-drawn SVG assets | Photos, logos, maps, and a one-off illustration that is not boxes and arrows. Not the path for compare / branch / steps. Images drift from tokens and cannot be edited as text |

Why not the other defaults:

- A new `::: compare` / `::: steps` directive would freeze a shape before the recipes have been used in deck repos. The markup already exists.
- Shipping illustration SVG from md-deck would be a theme. This repo does not ship a theme.
- Allowing raw SVG in slides would bypass the contract for every deck, not just diagrams.

Phased:

1. **Now.** Document the limits, the policy, and the three recipes, including before/after. Check cover titles. Balance automatic title wraps with CSS. Size diagram boxes with tokens (`flow_node_max_width`, `flow_node_min_height`, `flow_preferred_height`, `flow_stack_gap`, `column_min_height`). Full leftover-height stretch is opt-in (`flow_fill_height` or `::: flow fill`). Do not bake a deck's frame or palette into those defaults.
2. **Next, in the skill repo.** Teach the copy budget and the pre-release PNG review in `yohei1126/agent-skills` `md-deck/SKILL.md`. md-deck will still not fail a merely dense slide. Overflow past 80% remains the generator gate.
3. **Later, only if a recipe fails in a real deck.** Add a small generator feature on this same pipeline (junction, step number, a columns option). Do not open a second diagram language.
4. **Escape hatch.** Keep relative images for non-diagram figures.

## Responsibility

| Piece | Where it lives |
| --- | --- |
| Words, slide order, which recipe to use | Deck repository (slides Markdown) |
| Colours, type, spacing, quiet kind tints | Deck repository (`deck_style.md` tokens and `css` fences) |
| Contract, layout, arrow routing, cover-title check, recipes, this policy | This repo |
| Authoring workflow and the pre-tag checklist | `yohei1126/agent-skills` (follow-up; not copied here) |

## Cover titles

An ATX heading is one line. A trailing `\` does **not** continue it. The break marker is `\n`, the same marker flow labels use:

```markdown
# First phrase\nSecond phrase
# 骨子を先に見せる\n色は抑えて残す {.cover}
```

The renderer emits `<br>` inside `h1.title`. `text-wrap: balance` does not reflow across that `<br>`.

### Which slide is the cover

- The first slide, always, unless its H1 has class `no-cover`.
- Any later slide whose H1 has class `cover`.
- If both classes are present, `cover` wins.

Those sections get `data-cover="true"` ([HOOKS.md](HOOKS.md)). Content slides may also use `\n`. The balance and wrap rules below apply only to covers. Every title, cover or not, rejects an empty `\n` segment and more than three lines.

### Rules the checker enforces

Display width: a wide character (CJK, `East_Asian_Width` W or F) counts as 2, any other character as 1.

| Rule | Check |
| --- | --- |
| Empty segment | `# Foo\n` or `# Foo\n\nBar` fails |
| Line count | More than 3 lines fails |
| Mid-phrase | A line that is only a function word or a Japanese particle fails. A line that **ends** with an opening bracket (`（「『【([`) or **starts** with a closing mark (`）」』】)]、。．，,.!?;；:：`) fails. A line that is only punctuation fails |
| Balance | With two or more lines, each line must be at least 4 display units, and `shortest / longest` must be at least `0.45` |
| CJK wrap | A single-line cover that contains CJK and whose estimated width is over `1.02` times the content box must use `\n`. When the first slide is only treated as a cover because it is first, the error also says to add `{.no-cover}` if that slide is content |
| Long wrap | A single-line cover whose estimated width is over `2.05` times the content box must use `\n`, in any language. The same `{.no-cover}` hint applies on an implicit first-slide cover |
| Leading particle | A later cover line that starts with へ を と の に で が は も or や (except forms like `への`) is a **warning**. The build still runs. A line that is only the particle remains an error |

Function words (whole line, ignoring surrounding punctuation, case-insensitive): a, an, the, of, to, and, or, for, in, on, with, by, at, from, as, vs, via, into, over, than, that, this, nor, but.

Particles (whole line): は が を に で と も の へ や から まで より ね よ か.

The content box is `page_width - page_padding_left - page_padding_right`. Omitted sides inherit `page_padding`. Defaults are `1280px`, `48px`, `48px`, and `font_size_title` `36px`. The width estimate treats a wide character as one em, a Latin character as `0.56em`, and a space as `0.33em`. If the font size or a padding is not a bare number or `px` (for example `2rem`), the wrap estimate is skipped and the structural rules still run.

A Latin cover that wraps **once** is allowed without `\n`. `text-wrap: balance` on `.title` evens those two lines. `line-break: strict` keeps punctuation from hanging (kinsoku). It does not find phrase boundaries.

### What authors and agents verify

The estimate is not Chromium. After `md-deck check`:

```bash
uv run md-deck build slides.md -o out/deck.pdf --png out/png
```

Open every slide whose section has `data-cover="true"` (the first PNG, plus any `{.cover}` slide). Reject a title that breaks mid-phrase or leaves a short orphan line. Fix it with `\n` at a phrase boundary and re-check.

`md-deck check` prints `file:line: message` and refuses to build while a cover title fails. That is the generator hook. It is not a dictionary and it is not a pixel test.
