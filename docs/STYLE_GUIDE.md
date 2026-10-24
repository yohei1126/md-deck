# Style Markdown and slide conventions

md-deck renders decks. It does not ship a visual theme. Each deck repository owns two Markdown files: slide content and a style file. The style file is both the human-readable style guide and the machine-readable theme.

The **input contract** (required front matter, schemas, asset paths, and `md-deck check` rules) is spelled out in [INPUT_FORMAT.md](INPUT_FORMAT.md). This page lists tokens and authoring conventions.

## Style file shape

A style file is Markdown with:

1. YAML front matter: theme tokens
2. Prose: guidance for authors (ignored by the generator)
3. Optional fenced `css` blocks: extra rules appended after the token CSS

Pass the file with `--style path/to/deck_style.md`, or set `style:` in the slides front matter. The CLI flag overrides front matter. If neither resolves to a file, the check fails.

`examples/deck_style.md` is a plain black-on-white sample that lists tokens. Copy it into a deck repo and change the values; do not treat it as a product look.

## Required vs optional tokens

Required (check fails if missing):

- `color_background`, `color_text`, `color_title`
- `font_family`, `font_size_body`

Optional tokens use the plain defaults in the table below when omitted. Unknown names fail the check. See [`schemas/style.schema.json`](../schemas/style.schema.json).

## Token schema

Bare numbers for lengths become `px`, except `line_height`, `font_weight_title`, and `font_weight_body`, which stay unitless. Strings are emitted as written (so you can pass `"1.5rem"` or a font stack). Colours must be valid CSS colour strings (`#rgb`, `#rrggbb`, `rgb()`, `hsl()`, or a named colour).

| Token | CSS variable | Plain default | Required | Role |
| --- | --- | --- | --- | --- |
| `page_width` | `--page-width` | `1280px` | no | Slide width |
| `page_height` | `--page-height` | `720px` | no | Slide height |
| `color_background` | `--color-background` | `#ffffff` | **yes** | Page background |
| `color_text` | `--color-text` | `#000000` | **yes** | Body text |
| `color_muted` | `--color-muted` | `#444444` | no | Secondary text (`.muted`) |
| `color_border` | `--color-border` | `#cccccc` | no | Generic border token |
| `color_title` | `--color-title` | `#000000` | **yes** | `h1`–`h3` / accent |
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
| `color_table_header_bg` | `--color-table-header-bg` | `#f0f0f0` | no | Table header fill |
| `color_table_border` | `--color-table-border` | `#cccccc` | no | Table cell borders |
| `font_family` | `--font-family` | `sans-serif` | **yes** | Font stack |
| `font_size_body` | `--font-size-body` | `22px` | **yes** | Body size |
| `font_size_title` | `--font-size-title` | `36px` | no | Title size |
| `font_size_key_message` | `--font-size-key-message` | `20px` | no | Key Message size |
| `font_size_question` | `--font-size-question` | `18px` | no | Question size |
| `font_size_small` | `--font-size-small` | `16px` | no | Tables and compact text |
| `font_weight_title` | `--font-weight-title` | `700` | no | Titles and labels |
| `font_weight_body` | `--font-weight-body` | `400` | no | Body weight |
| `line_height` | `--line-height` | `1.45` | no | Body line height |
| `page_padding` | `--page-padding` | `48px` | no | Inset inside the slide |
| `gap` | `--gap` | `16px` | no | Flex gaps |
| `card_radius` | `--card-radius` | `8px` | no | Column / flow corner radius |
| `card_padding` | `--card-padding` | `16px` | no | Inner padding for boxes |
| `key_message_radius` | `--key-message-radius` | `8px` | no | Key Message radius |
| `question_radius` | `--question-radius` | `8px` | no | Question radius |
| `border_width` | `--border-width` | `1px` | no | Default border width |
| `flow_node_min_width` | `--flow-node-min-width` | `120px` | no | Minimum flow node width |
| `flow_node_padding` | `--flow-node-padding` | `12px` | no | Flow node padding |

## Optional CSS fence

```css
.slide h1 {
  letter-spacing: 0.02em;
}
```

Rules from every `css` fence in the style file are appended after the generated `:root` block. `--css file.css` on the CLI appends still later.

## Slide Markdown conventions

| Construct | Syntax | Check rule |
| --- | --- | --- |
| Slide break | a line that is exactly `---` | no empty slide from a trailing `---` |
| Title | exactly one `# Heading` per slide | missing / extra H1 fail |
| Key Message | at most one `**Key Message:** …` line | extras fail |
| Question box | `::: question` … `:::` | non-empty; known kinds only |
| Flow | `::: flow` with `A -> B` … `:::` | ≥2 nodes; no empty node |
| Columns | `::: columns` split by `+++` … `:::` | ≥2 non-empty columns; `+++` only inside |
| Table / lists | normal Markdown | consistent table columns; list indent sanity |
| Code fence | ` ``` ` … ` ``` ` | must close |
| HTML | not used by default | fails unless `--allow-html` |

Slides front matter must include `title`, `version`, `date`, `lang`, and `style` (see [INPUT_FORMAT.md](INPUT_FORMAT.md)).

## Overflow

After layout, each slide scales down in 2% steps to 80% if content overflows. If it still overflows, the build fails and names the slide numbers. Shorten the copy or adjust tokens (font sizes, padding) in the style file.

## Japanese guide

See [STYLE_GUIDE.ja.md](STYLE_GUIDE.ja.md) for the same material in Japanese.
