# Style Markdown and slide conventions

md-deck renders decks. It does not ship a visual theme. Each deck repository owns two Markdown files: slide content and a style file. The style file is both the human-readable style guide and the machine-readable theme.

## Style file shape

A style file is Markdown with:

1. YAML front matter: theme tokens
2. Prose: guidance for authors (ignored by the generator)
3. Optional fenced `css` blocks: extra rules appended after the token CSS

Pass the file with `--style path/to/deck_style.md`, or set `style: deck_style.md` in the slides front matter. If neither is set, the build fails with a clear error.

`examples/deck_style.md` is a plain black-on-white sample that lists every token. Copy it into a deck repo and change the values; do not treat it as a product look.

## Token schema

Bare numbers for lengths become `px`, except `line_height`, `font_weight_title`, and `font_weight_body`, which stay unitless. Strings are emitted as written (so you can pass `"1.5rem"` or a font stack).

| Token | CSS variable | Plain default | Role |
| --- | --- | --- | --- |
| `page_width` | `--page-width` | `1280px` | Slide width |
| `page_height` | `--page-height` | `720px` | Slide height (16:9 with default width) |
| `color_background` | `--color-background` | `#ffffff` | Page background |
| `color_text` | `--color-text` | `#000000` | Body text |
| `color_muted` | `--color-muted` | `#444444` | Secondary text (`.muted`) |
| `color_border` | `--color-border` | `#cccccc` | Generic border token |
| `color_title` | `--color-title` | `#000000` | `h1`–`h3` |
| `color_key_message_bg` | `--color-key-message-bg` | `#f5f5f5` | Key Message box fill |
| `color_key_message_text` | `--color-key-message-text` | `#000000` | Key Message text |
| `color_key_message_border` | `--color-key-message-border` | `#cccccc` | Key Message border |
| `color_question_bg` | `--color-question-bg` | `#f5f5f5` | Question box fill |
| `color_question_text` | `--color-question-text` | `#000000` | Question text |
| `color_question_border` | `--color-question-border` | `#cccccc` | Question border |
| `color_card_bg` | `--color-card-bg` | `#ffffff` | Column card fill |
| `color_card_border` | `--color-card-border` | `#cccccc` | Column card border |
| `color_flow_node_bg` | `--color-flow-node-bg` | `#ffffff` | Flow node fill |
| `color_flow_node_border` | `--color-flow-node-border` | `#000000` | Flow node border |
| `color_flow_arrow` | `--color-flow-arrow` | `#000000` | Flow arrow stroke |
| `color_table_header_bg` | `--color-table-header-bg` | `#f0f0f0` | Table header fill |
| `color_table_border` | `--color-table-border` | `#cccccc` | Table cell borders |
| `font_family` | `--font-family` | `sans-serif` | Font stack |
| `font_size_body` | `--font-size-body` | `22px` | Body size |
| `font_size_title` | `--font-size-title` | `36px` | Title size |
| `font_size_key_message` | `--font-size-key-message` | `20px` | Key Message size |
| `font_size_question` | `--font-size-question` | `18px` | Question size |
| `font_size_small` | `--font-size-small` | `16px` | Tables and compact text |
| `font_weight_title` | `--font-weight-title` | `700` | Titles and labels |
| `font_weight_body` | `--font-weight-body` | `400` | Body weight |
| `line_height` | `--line-height` | `1.45` | Body line height |
| `page_padding` | `--page-padding` | `48px` | Inset inside the slide |
| `gap` | `--gap` | `16px` | Flex gaps |
| `card_radius` | `--card-radius` | `8px` | Column / flow corner radius |
| `card_padding` | `--card-padding` | `16px` | Inner padding for boxes |
| `key_message_radius` | `--key-message-radius` | `8px` | Key Message radius |
| `question_radius` | `--question-radius` | `8px` | Question radius |
| `border_width` | `--border-width` | `1px` | Default border width |
| `flow_node_min_width` | `--flow-node-min-width` | `120px` | Minimum flow node width |
| `flow_node_padding` | `--flow-node-padding` | `12px` | Flow node padding |

Unknown token names fail the build. Omitted tokens take the plain defaults above so a partial front matter still renders; they are not a brand theme.

## Optional CSS fence

```css
.slide h1 {
  letter-spacing: 0.02em;
}
```

Rules from every `css` fence in the style file are appended after the generated `:root` block. `--css file.css` on the CLI appends still later.

## Slide Markdown conventions

| Construct | Syntax |
| --- | --- |
| Slide break | a line that is exactly `---` |
| Title | `# Heading` (first heading on the slide) |
| Key Message | `**Key Message:** ...` on its own line |
| Question box | `::: question` … `:::` |
| Flow | `::: flow` with `A -> B -> C` (or one node per line) … `:::` |
| Columns | `::: columns` with columns separated by a `+++` line … `:::` |
| Table / lists | normal Markdown |

Front matter on the slides file may include `title:` (PDF title) and `style:` (path to the style Markdown, relative to the slides file).

## Overflow

After layout, each slide scales down in 2% steps to 80% if content overflows. If it still overflows, the build fails and names the slide numbers. Shorten the copy or adjust tokens (font sizes, padding) in the style file.

## Japanese guide

See [STYLE_GUIDE.ja.md](STYLE_GUIDE.ja.md) for the same material in Japanese.
