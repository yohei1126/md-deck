---
# Plain demonstration style: black text on white, one font, no brand colours.
# Real decks replace this file in their own repo. md-deck does not ship a theme.

page_width: 1280
page_height: 720

color_background: "#ffffff"
color_text: "#000000"
color_muted: "#444444"
color_gray: "#444444"
color_border: "#cccccc"
color_title: "#000000"
color_top_bar: "#000000"
color_accent_2: "#666666"
color_highlight: "#000000"
color_highlight_bg: "#f0f0f0"

color_key_message_bg: "#f5f5f5"
color_key_message_text: "#000000"
color_key_message_border: "#cccccc"

color_question_bg: "#f5f5f5"
color_question_text: "#000000"
color_question_border: "#cccccc"

color_card_bg: "#ffffff"
color_card_border: "#cccccc"

color_flow_node_bg: "#ffffff"
color_flow_node_border: "#000000"
color_flow_arrow: "#000000"

color_table_header_bg: "#eeeeee"
color_table_border: "#cccccc"

font_family: "Noto Sans CJK JP, Noto Sans JP, DejaVu Sans, sans-serif"
font_size_body: 22
font_size_title: 36
font_size_key_message: 20
font_size_question: 18
font_size_small: 16
font_size_table: 16
font_weight_title: 700
font_weight_body: 400
line_height: 1.45

page_padding: 48
page_padding_top: 48
page_padding_right: 48
page_padding_bottom: 48
page_padding_left: 48
footer_inset_bottom: 0.6em
footer_inset_right: 0
gap: 16
card_radius: 8
card_padding: 16
key_message_radius: 8
question_radius: 8
border_width: 1
flow_node_min_width: 120
flow_node_max_width: 240
flow_node_min_height: 148
column_min_height: 160
flow_node_padding: 12

# Optional; when omitted, defaults follow slides lang (en/ja).
# label_question: "Question"
# label_key_message: "Key Message"
# label_source: "Source:"   # empty string hides the footer prefix
# source_label_weight: 600    # .source .label weight
# source_label_gap: 0.15em    # gap after .source .label (0 removes it)
# flow_edge_shape: orthogonal  # or straight
# flow_callout_gap: 12
# flow_port_gap: 12
question_label_placement: inline
page_number_placement: bottom-right
---

# Example deck style (plain)

This file is an **example only**. It shows tokens the generator reads and uses a neutral black-on-white look so CI can build `examples/sample.md` without shipping a product theme.

Deck repositories keep their own style Markdown (front matter tokens plus human-readable guidance). Humans and tools such as NotebookLM can read the prose; md-deck ignores prose and only uses:

1. YAML front matter tokens (above)
2. Optional fenced `css` blocks for extra rules

Style CSS should target the stable hooks in [HOOKS.md](../docs/HOOKS.md) (for example `.flow-node[data-kind="doc"]`), not `#slide-N … :nth-child()` selectors.

## English note

Tokens drive CSS variables. Omit a token and the generator fills a plain default listed in `docs/STYLE_GUIDE.md`. There is no built-in brand palette inside md-deck.

## 日本語メモ

このファイルは形式の見本です。色やフォントの本番指定は、各デッキ用リポジトリのスタイル Markdown に置きます。md-deck 本体にはデザインやブランド色は含まれません。見た目のフックは [HOOKS.md](../docs/HOOKS.md) を参照してください。

```css
/* Optional extra rules. Example: slightly tighter lists in this sample. */
.slide li {
  margin-top: 0.3em;
}

.flow-node[data-kind="doc"] {
  font-weight: 700;
}

.flow-node[data-kind="muted"] {
  color: var(--color-muted);
}

.flow-node[data-kind="highlight"] {
  background: var(--color-highlight-bg);
  border-color: var(--color-highlight);
}

/* Optional cover frame. Not applied: md-deck does not ship a frame or a brand band.
   Uncomment in a deck style when a quiet border and a larger title are wanted.
   Keep colours on the tokens above; do not paste a product palette here.

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
*/
```
