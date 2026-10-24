# md-deck

md-deck turns one Markdown file into a clean 16:9 PDF slide deck. Same source bytes produce the same PDF. The tool owns layout and rendering only: page size, overflow checks, flow arrows, footers, and the build pipeline.

**Content and visual style live in the deck repository**, not in md-deck. Each deck supplies:

- a slides Markdown file
- a style Markdown file (YAML theme tokens, optional CSS fence, plus human-readable guidance)

This repository’s `examples/` folder holds sample slides and a plain sample style so you can try the generator. Those files are examples only. Real decks, styles, and generated PDFs are managed in the repos that call md-deck (or its GitHub Action). md-deck does not ship a default theme; a style file is required.

## Install

Uses [uv](https://docs.astral.sh/uv/). From a clone:

```bash
uv sync
uv run playwright install chromium
```

Or run a pinned tag straight from GitHub without a local clone:

```bash
uvx --from git+https://github.com/yohei1126/md-deck@v0.1.0 md-deck \
  check slides.md
uvx --from git+https://github.com/yohei1126/md-deck@v0.1.0 md-deck \
  build slides.md -o out.pdf
```

Japanese decks need a CJK font on the machine that renders PDF, for example `fonts-noto-cjk` on Debian/Ubuntu. md-deck is not published to PyPI yet; install from Git or use the Action.

## Usage

Validate without Chromium (prints every problem as `file:line: message`):

```bash
uv run md-deck check examples/sample.md
```

Build (runs the same validation first, then refuses to render on errors):

```bash
uv run md-deck build examples/sample.md -o out/sample.pdf
```

`--style path` overrides the slides front matter `style:` key. Front matter must name a style file when you omit the flag.

Useful `build` flags:

| Flag | Meaning |
| --- | --- |
| `-o PATH` | Output PDF (required) |
| `--style PATH` | Style Markdown (overrides front matter) |
| `--css PATH` | Extra CSS after the style file (repeatable) |
| `--png DIR` | Write one PNG per slide |
| `--html PATH` | Keep the intermediate HTML |
| `--check-deterministic` | Build twice and fail if PDF bytes differ |
| `--allow-html` | Allow raw HTML in slides (off by default) |

Exit is non-zero if validation fails, or if a slide still overflows after shrinking to 80% of its layout scale.

## Input contract and conventions

Required slides front matter: `title`, `version`, `date` (yyyy-mm-dd), `lang`, `style`. Optional: `subtitle`, `author`, `audience`. Unknown keys fail the check. `lang` sets `<html lang>` and default question / key-message labels.

Required style tokens: `color_background`, `color_text`, `color_title`, `font_family`, `font_size_body`. Other tokens are optional with plain defaults (`0` / `none` allowed on radii and borders; per-side `page_padding_*`; label and accent colour tokens). Schemas: [`schemas/slides.schema.json`](schemas/slides.schema.json), [`schemas/style.schema.json`](schemas/style.schema.json).

Full contract and flow syntax (labelled / dashed / parallel arrows, orthogonal `link:` routes, node ids / chips / stacks / callouts, flow inside columns, sources): [docs/INPUT_FORMAT.md](docs/INPUT_FORMAT.md). Token tables: [docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md) / [docs/STYLE_GUIDE.ja.md](docs/STYLE_GUIDE.ja.md). Stable CSS hooks (including SVG `.flow-arrow` / `.flow-label`): [docs/HOOKS.md](docs/HOOKS.md).

Slide conventions in short: slides separated by `---`; exactly one `#` title per slide (optional `{#id .class}`); at most one `**Key Message:**`; `::: question` / `::: flow` / `::: columns` / `::: source` (flow may nest inside columns); trailing `\` for hard breaks; footer page numbers as `n / total` with `page_number_placement`.

## Style and content split

| Piece | Where it lives | Role |
| --- | --- | --- |
| Slides `.md` | Deck repo | Front matter + titles, Key Message, lists, tables, flow, columns, questions, sources |
| Style `.md` | Deck repo | Tokens (colours, fonts, spacing, labels) + prose style guide + optional `css` targeting [HOOKS.md](docs/HOOKS.md) |
| md-deck | This repo | Check contract, parse Markdown, apply style tokens, render with headless Chromium |

## Determinism

The HTML→PDF step uses Chromium through Playwright. After writing the PDF, md-deck rewrites CreationDate and ModDate to a fixed timestamp and sets Producer/Creator to `md-deck`, so metadata clocks do not change the file. Fonts and Chromium version still need to match across environments for pixel-identical pages; pin those in CI the same way you pin the Action.

## GitHub Action

Composite action at the repo root (`action.yml`). Inputs: `source`, `output`, optional `style` / `css`, and `check-only` (validate without installing Chromium or writing a PDF). Builds always validate first.

```yaml
- uses: yohei1126/md-deck@v0.1.0
  with:
    source: deck/slides.md
    style: deck/deck_style.md
    output: dist/deck.pdf
```

Check-only:

```yaml
- uses: yohei1126/md-deck@v0.1.0
  with:
    source: deck/slides.md
    check-only: "true"
```

Pin a release tag when you consume the action. This repository does not create tags or releases as part of normal development; cut them deliberately when you publish.

### Example: build on deck tags and attach to the release

In a **deck** repository (not required here):

```yaml
name: Release deck
on:
  push:
    tags: ["deck-*"]

jobs:
  pdf:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: yohei1126/md-deck@v0.1.0
        with:
          source: slides.md
          style: deck_style.md
          output: dist/deck.pdf
      - uses: softprops/action-gh-release@v2
        with:
          files: dist/deck.pdf
```

## License

Apache License 2.0. See [LICENSE](LICENSE).
