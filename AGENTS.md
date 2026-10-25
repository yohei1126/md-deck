# AGENTS.md

Guidance for coding agents working on **md-deck** (Markdown → 16:9 PDF generator and GitHub Action).

## What this repo is

- Layout, validation, rendering, and the reusable Action live here.
- Real slide content, `deck_style.md`, brand CSS, and Release PDFs live in **deck repositories**, not here.
- `examples/` is sample input only.

## Slide-deck practice (read this)

When creating or revising decks that **use** md-deck (including work in other repos), follow:

**[md-deck skill (yohei1126/agent-skills)](https://github.com/yohei1126/agent-skills/blob/main/md-deck/SKILL.md)**

That skill covers workflow, style vs content, spacing/density, review before tag/release, and common failures. Do not invent unsupported Markdown directives.

The generator rules below live in this repo. The skill's authoring checklist is updated separately in [yohei1126/agent-skills](https://github.com/yohei1126/agent-skills/blob/main/md-deck/SKILL.md) when that checklist should match. Do not paste the skill into this repository.

## Docs in this repo

| Doc | Topic |
| :--- | :--- |
| [README.md](README.md) | Install, CLI, Action |
| [docs/INPUT_FORMAT.md](docs/INPUT_FORMAT.md) | Slides contract and flow syntax |
| [docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md) / [STYLE_GUIDE.ja.md](docs/STYLE_GUIDE.ja.md) | Style tokens |
| [docs/HOOKS.md](docs/HOOKS.md) | Stable CSS hooks |
| [docs/VISUAL_POLICY.md](docs/VISUAL_POLICY.md) | Readability policy, expression limits, phased plan, cover titles |
| [docs/DIAGRAMS.md](docs/DIAGRAMS.md) | Compare / branch / 3-step recipes and before/after |

## Visual policy

Slide materials should read the way a NotebookLM slide reads: tidy colour, structured information, and a visible bone of boxes, arrows, and branches. Do not chase decoration (gradients, shadows, stickers, icon collages).

When writing or editing slides that use md-deck:

- One idea per slide. A node label is a name, not a sentence.
- Compare with `::: columns` (`panel` when the box should show, `plain` when it should not). Do not fake a comparison with an arrow.
- Branch with one box and one arrow per outcome. Do not write "A or B" inside a single node. `Start -> { A / B }` draws one arrow into the stack; fan into each member with a separate edge (see [docs/DIAGRAMS.md](docs/DIAGRAMS.md)).
- Put three steps in one `::: flow wide` row of short labels. The row is centred with even gaps, and the boxes share the row (`flow_node_max_width` defaults to `none`). That wide row grows toward `flow_preferred_height` (default `60%` of the slide) and the panel stays that tall. A plain flow stays content height. The title stays at the top; blocks under it are centred in the leftover space. A trailing question stays at the bottom, with leftover space split under the heading and above the question. `flow_fill_height: fill` or `::: flow fill` stretches boxes to the leftover slide height. `steps` adds a muted index. A node beside a stack stays as wide as its label. A one-line conclusion over three cards is `::: columns` split into three parts (see [docs/DIAGRAMS.md](docs/DIAGRAMS.md)).
- A `{ A / B }` stack separates its boxes by `flow_stack_gap` (default `32px`), in addition to the 72px trunk gap beside the stack.
- A deck style must not set `.flow-row { justify-content: space-between }`. It cancels the centred row. Remove that rule when adopting these defaults. Frames, accent bands, and brand colours stay in the deck style, not in base CSS.
- A branch into a stack uses a shared trunk and at least 72px of gap. Do not leave the arrowheads in the corners.
- Cover slides (`data-cover`) are centred. Front matter `subtitle` and `date` render under the title. A content slide that is first needs `{.no-cover}`.
- Keep colours inside the style tokens. Base CSS does not paint node kinds; a deck style may tint `muted` / `highlight` quietly.
- Do not add customer or proposal content to this repo. `examples/` stays generic.

Full limits and the phased plan: [docs/VISUAL_POLICY.md](docs/VISUAL_POLICY.md). Buildable pairs: [examples/diagram_patterns.md](examples/diagram_patterns.md).

## Cover titles

The cover is the first slide, or any H1 with class `cover`. `{.no-cover}` opts the first slide out. The section is marked `data-cover="true"`.

- Do not break a cover title mid-phrase. ATX headings are one line; a trailing `\` does not continue them. Write `\n` at a phrase boundary: `# First phrase\nSecond phrase`.
- Prefer balanced lines. `md-deck check` rejects an empty segment, more than three lines, a line that is only a function word or a Japanese particle, a line that starts or ends on the wrong side of a bracket, and a pair whose shorter display width is under about half the longer one (a wide character counts as two).
- A Japanese cover that would wrap on its own must include `\n`. A title that would wrap past two lines must include `\n` in any language. A Latin cover that wraps once is evened with `text-wrap: balance` on `.title`.
- Front matter `title` is the PDF document title. `subtitle` and `date` render as `.cover-meta`. `author` and `audience` are not drawn. A frame or a larger cover title is optional deck CSS (see [docs/VISUAL_POLICY.md](docs/VISUAL_POLICY.md)), not a built-in chrome.
- After `md-deck check`, render PNG and look at every `data-cover="true"` slide: `md-deck build slides.md -o out.pdf --png out/png`. The width estimate is not a layout engine. Thresholds are in [docs/VISUAL_POLICY.md](docs/VISUAL_POLICY.md).

## Agent constraints

- Prefer PRs over direct pushes to the default branch.
- Pin Action consumers to a release tag or full commit SHA (never a floating major that can break CI).
- Do not cut tags/releases unless the owner asked.
- Do not put customer or proposal content into this repository.
