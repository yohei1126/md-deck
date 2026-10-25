# Visual policy

md-deck should produce slide materials that are as easy to read as a NotebookLM slide, without becoming a flashy deck. Colour stays quiet. Information is structured. The bone of a diagram — boxes, arrows, and branches — is obvious.

This page is the generator-side record of that policy: what the HTML/CSS → PDF path can draw today, what it cannot, which approach to take, and how cover titles may break. Recipes and before/after markup are in [DIAGRAMS.md](DIAGRAMS.md). Tokens stay in [STYLE_GUIDE.md](STYLE_GUIDE.md). The authoring skill in [yohei1126/agent-skills](https://github.com/yohei1126/agent-skills/blob/main/md-deck/SKILL.md) is updated separately; do not copy it into this repo.

## Policy

- One idea per slide. The Key Message is one sentence.
- A diagram label is a name, not a sentence. Aim for about four English words or about twelve CJK characters. The checker does not enforce that budget yet.
- Compare two things with `::: columns`. Use `panel` when the box border should show (the default `.column` border already does; `panel` is the hook). Use `plain` only when the border should disappear. Do not draw a comparison as an arrow.
- Branch with one box and one arrow per outcome. Do not put "A or B" inside a single node.
- Show a short procedure as one horizontal row: `::: flow wide` with three short labels.
- Colours come from style tokens: background, text, one quiet accent, a muted secondary. No gradients, drop shadows, stickers, or icon collages in the style CSS.
- Node kinds (`actor`, `system`, `doc`, `muted`, `highlight`) are hooks. Base CSS does not paint them differently. A deck may tint `muted` / `highlight` with the existing tokens. It should not invent a bright per-kind palette.
- Photos, logos, and maps may be images. Boxes-and-arrows should not be images.
- Shrink-to-fit (down to 80%) is a last resort. Cut the copy before relying on it.

`examples/` in this repo stays generic. Customer and proposal copy belongs in the deck repository.

## What the pipeline can draw

The path is fixed:

1. Markdown is checked and turned into HTML (`::: flow`, `::: columns`, tables, lists, one H1, one Key Message).
2. Style tokens become CSS variables. Optional `css` fences and `--css` append after `base.css`.
3. Headless Chromium lays out the page. `deck.js` measures the flow DOM and draws SVG arrows.
4. Chromium prints a 16:9 PDF. If a slide still overflows after scaling to 80%, the build fails.

Stable classes are [HOOKS.md](HOOKS.md). Arrow path geometry is not stable; the classes and `data-*` hooks are.

| Piece | Today |
| --- | --- |
| Horizontal steps | `A -> B -> C`. `::: flow wide` keeps one row (`flex-wrap: nowrap`, space-between) |
| Two-up compare | `::: columns` / `panel` / `plain`, split with `+++`. A column may contain one nested `::: flow` |
| Branch | A `{ A / B }` stack plus a separate edge into each member. Same-row fan-out is also routed (trunks nest, ports stay apart) |
| Lanes and cross-links | `lane:` and `link:` with `route=` (`between`, `down`, `up`, `left`, `right`, `auto`) |
| Edge shapes | Orthogonal (default) or straight. Dashed, labelled, and bidirectional arrows |
| Node chrome | One rectangle. Caption, badge, chips, callout. Kinds are data attributes |
| Tables, lists, question, source, footer page number | Yes |
| Images | Relative paths that stay inside the slides directory |
| Title wrap | `text-wrap: balance` and `line-break: strict` on `.title`. Explicit `\n` in an H1 becomes `<br>` |
| Cover mark | First `<section>` gets `data-cover="true"`, as does any slide whose H1 has class `cover` |

There is no separate cover layout. The cover is a normal slide that follows the title rules below. Front matter `title` is the PDF document title (`<title>`). `subtitle`, `author`, and `audience` are validated and are not rendered. A visible subtitle is a line in the slide body.

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
- A built-in icon set, gradient, or shadow. A deck style file could add them. This policy says not to.

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

1. **Now.** Document the limits, the policy, and the three recipes, including before/after. Check cover titles. Balance automatic title wraps with CSS.
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
| CJK wrap | A single-line cover that contains CJK and whose estimated width is over `1.02` times the content box must use `\n` |
| Long wrap | A single-line cover whose estimated width is over `2.05` times the content box must use `\n`, in any language |

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
