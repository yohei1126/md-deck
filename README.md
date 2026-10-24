# md-deck

md-deck turns one Markdown file into a clean 16:9 PDF slide deck. Same source bytes produce the same PDF. The tool owns layout and rendering only: page size, overflow checks, flow arrows, and the build pipeline.

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
  slides.md -o out.pdf --style deck_style.md
```

Japanese decks need a CJK font on the machine that renders PDF, for example `fonts-noto-cjk` on Debian/Ubuntu. md-deck is not published to PyPI yet; install from Git or use the Action.

## Usage

```bash
uv run md-deck examples/sample.md -o out/sample.pdf --style examples/deck_style.md
```

Or set `style: deck_style.md` in the slides front matter and omit `--style`.

Useful flags:

| Flag | Meaning |
| --- | --- |
| `-o PATH` | Output PDF (required) |
| `--style PATH` | Style Markdown (required unless set in slides front matter) |
| `--css PATH` | Extra CSS after the style file (repeatable) |
| `--png DIR` | Write one PNG per slide |
| `--html PATH` | Keep the intermediate HTML |
| `--check-deterministic` | Build twice and fail if PDF bytes differ |

Exit is non-zero if a slide still overflows after shrinking to 80% of its font/layout scale.

## Style and content split

| Piece | Where it lives | Role |
| --- | --- | --- |
| Slides `.md` | Deck repo | Titles, Key Message, lists, tables, flow, columns, questions |
| Style `.md` | Deck repo | Tokens (colours, fonts, spacing) + prose style guide + optional `css` |
| md-deck | This repo | Parse Markdown, apply style tokens, render with headless Chromium |

Token schema, fences, and slide conventions: [docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md) (English) and [docs/STYLE_GUIDE.ja.md](docs/STYLE_GUIDE.ja.md) (Japanese).

Slide conventions in short: slides separated by `---`; `#` title; `**Key Message:**`; `::: question`; `::: flow` with `A -> B`; `::: columns` split by `+++`.

## Determinism

The HTML→PDF step uses Chromium through Playwright. After writing the PDF, md-deck rewrites CreationDate and ModDate to a fixed timestamp and sets Producer/Creator to `md-deck`, so metadata clocks do not change the file. Fonts and Chromium version still need to match across environments for pixel-identical pages; pin those in CI the same way you pin the Action.

## GitHub Action

Composite action at the repo root (`action.yml`). Inputs: `source`, `output`, optional `style`, optional `css`. It installs uv, syncs this project from the Action checkout, installs Playwright Chromium, then runs `md-deck`.

```yaml
- uses: yohei1126/md-deck@v0.1.0
  with:
    source: deck/slides.md
    style: deck/deck_style.md
    output: dist/deck.pdf
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
