---
# Opt-in role palette. Sample builds use examples/deck_style.md (plain).
# theme fills omitted colour tokens. Set a colour token to override one role.
# When to use a role: https://github.com/yohei1126/agent-skills/blob/main/visual-color/SKILL.md
# Diagrams: https://github.com/yohei1126/agent-skills/blob/main/visual-diagram/SKILL.md
theme: dark-blue

page_width: 1280
page_height: 720

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
flow_node_max_width: none
flow_node_min_height: 96
flow_preferred_height: 60%
flow_stack_gap: 32
column_min_height: 160
flow_node_padding: 12

question_label_placement: inline
page_number_placement: bottom-right
---

# dark-blue

`theme: dark-blue` fills omitted colour tokens. The ground is `#EDE8E4`, text is `#333333`, navy `#073365` is titles, node borders, and arrows, and `#F7581D` is the accent. This file does not repeat those hex values so the theme stays the source.

`examples/sample.md` and `examples/diagram_patterns.md` keep `style: deck_style.md`. Point a deck at this file, or copy the `theme` line, when you want the palette.

```css
.flow-node[data-kind="muted"] {
  color: var(--color-muted);
}

.flow-node[data-kind="highlight"] {
  background: var(--color-highlight-bg);
  border-color: var(--color-highlight);
}
```
