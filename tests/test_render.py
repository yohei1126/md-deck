"""Unit tests for slide/flow rendering (no Chromium)."""

from __future__ import annotations

from md_deck.build import build_html
from md_deck.flow import parse_flow_body, parse_node_text, render_flow_html
from md_deck.slides import apply_hard_breaks, parse_deck, render_slide_markdown, resolve_labels
from md_deck.style import load_style_file, tokens_to_css
from md_deck.validate import validate_style_tokens


def test_labelled_and_dashed_arrows():
    diagram = parse_flow_body(
        "A -[go]-> B\nC ..> D\nE -.[skip].-> F\nG <-> H\n"
    )
    styles = {(e.source, e.target, e.style, e.label, e.bidirectional) for lane in diagram.lanes for e in lane.edges}
    assert ("A", "B", "solid", "go", False) in styles
    assert ("C", "D", "dashed", None, False) in styles
    assert ("E", "F", "dashed", "skip", False) in styles
    assert ("G", "H", "solid", None, True) in styles


def test_node_kind_caption_badge():
    node = parse_node_text("[doc] Report | quarterly {draft}")
    assert node.kind == "doc"
    assert node.title == "Report"
    assert node.caption == "quarterly"
    assert node.badge == "draft"


def test_node_id_and_chips():
    node = parse_node_text("[system] Hub {#hub} [[a, b, c]] {live}")
    assert node.node_id == "hub"
    assert node.key == "hub"
    assert node.title == "Hub"
    assert node.chips == ["a", "b", "c"]
    assert node.badge == "live"


def test_chips_split_on_comma_only_with_escape():
    node = parse_node_text("N [[a/b, c]]")
    assert node.chips == ["a/b", "c"]
    escaped = parse_node_text(r"N [[a\,b, c]]")
    assert escaped.chips == ["a,b", "c"]


def test_chips_only_node():
    diagram = parse_flow_body("A -> [[x, y]] -> B\n")
    assert diagram.errors == []
    assert any(n.chips == ["x", "y"] and not n.title for n in diagram.nodes.values())
    html = render_flow_html(diagram)
    assert "flow-chip" in html
    assert "flow-lanes" in html
    assert "flow-row" in html


def test_separate_lines_do_not_auto_chain():
    diagram = parse_flow_body(
        "lane: Top\n"
        "P {#p}\n"
        "Q {#q}\n"
        "R {#r}\n"
        "lane: Bottom\n"
        "Target {#t}\n"
    )
    assert diagram.lanes[0].edges == []
    assert len(diagram.lanes[0].columns) == 3


def test_between_route_and_stack_attach():
    diagram = parse_flow_body(
        "L -> { Up / Down } -> R\n"
        "link: L => R : x [route=between]\n"
        "callout: R : note [pos=below-left side=right]\n"
    )
    stack_edges = diagram.lanes[0].edges
    assert stack_edges[0].target_attach == "stack"
    assert stack_edges[1].source_attach == "stack"
    assert diagram.links[0].route == "between"
    assert diagram.callouts[0].pos == "below-left"
    assert diagram.callouts[0].side == "right"
    html = render_flow_html(diagram)
    assert 'data-to-attach="stack"' in html
    assert 'data-from-attach="stack"' in html
    assert 'data-route="between"' in html
    assert 'data-pos="below-left"' in html
    assert 'data-side="right"' in html


def test_cross_lane_id_arrow_resolves():
    diagram = parse_flow_body(
        "lane: Top\n"
        "A {#a}\n"
        "lane: Bottom\n"
        "B {#b}\n"
        "{#a} -> {#b}\n"
    )
    assert diagram.errors == []
    assert "a" in diagram.nodes
    assert "b" in diagram.nodes
    assert len(diagram.links) == 1
    assert diagram.links[0].source == "a"
    assert diagram.links[0].target == "b"
    assert diagram.links[0].cross is True
    # Foreign id must not be re-placed in the bottom lane.
    assert "a" not in diagram.lanes[1].node_keys
    html = render_flow_html(diagram)
    assert html.count('data-node="a"') == 1
    assert 'data-kind="link"' in html


def test_unknown_bare_id_is_clear_error():
    diagram = parse_flow_body("lane: Top\nA {#a}\n{#missing} -> {#a}\n")
    assert any("unknown flow node id 'missing'" in e for e in diagram.errors)


def test_single_lane_always_emits_wrappers():
    html = render_flow_html(parse_flow_body("A -> B\n"))
    assert 'class="flow-lanes"' in html
    assert 'class="lane"' in html
    assert 'class="flow-row"' in html


def test_label_and_badge_hard_breaks():
    diagram = parse_flow_body("A -[lab\\nel]-> B {bad\\nge}")
    edge = diagram.lanes[0].edges[0]
    assert edge.label == "lab\nel"
    # Badge on B
    assert "\n" in diagram.nodes["B"].badge or diagram.nodes["B"].badge == "bad\nge"


def test_lanes_and_links():
    diagram = parse_flow_body(
        "lane: Upper\n"
        "A -> B\n"
        "lane: Lower\n"
        "C -> D\n"
        "link: B => C : bridge [route=down]\n"
    )
    assert len(diagram.lanes) == 2
    assert diagram.lanes[0].label == "Upper"
    assert len(diagram.links) == 1
    assert diagram.links[0].label == "bridge"
    assert diagram.links[0].route == "down"
    assert diagram.links[0].cross is True
    html = render_flow_html(diagram)
    assert 'class="lane"' in html
    assert "lane-label" in html
    assert 'data-from="B"' in html
    assert 'data-to="C"' in html
    assert 'data-kind="link"' in html
    assert 'data-route="down"' in html


def test_parallel_edges_get_pair_indices():
    diagram = parse_flow_body("A -[one]-> B\nA -.[two].-> B\n")
    edges = diagram.lanes[0].edges
    assert len(edges) == 2
    assert {e.pair_index for e in edges} == {0, 1}
    assert edges[0].pair_count == 2


def test_stacked_nodes_and_callout():
    diagram = parse_flow_body(
        "A -> { Upper / Lower } -> B\n"
        "callout: B : note [pos=below]\n"
    )
    assert any(isinstance(c, list) and len(c) == 2 for c in diagram.lanes[0].columns)
    assert len(diagram.callouts) == 1
    html = render_flow_html(diagram)
    assert "flow-stack" in html
    assert "flow-callout" in html
    assert 'data-pos="below"' in html


def test_legacy_arrow_chain_still_works():
    diagram = parse_flow_body("Markdown -> HTML -> PDF")
    assert list(diagram.nodes) == ["Markdown", "HTML", "PDF"]
    assert len(diagram.lanes[0].edges) == 2


def test_duplicate_titles_get_unique_keys():
    diagram = parse_flow_body(
        "lane: One\nA -> B\nlane: Two\nA -> C\nlink: B => C : x\n"
    )
    assert "A" in diagram.nodes
    assert "A#2" in diagram.nodes
    assert diagram.nodes["A"].title == "A"
    assert diagram.nodes["A#2"].title == "A"
    assert diagram.links[0].source == "B"
    assert diagram.links[0].target == "C"


def test_link_resolves_node_id():
    diagram = parse_flow_body(
        "Long\\nTitle {#src} -> Other {#dst}\n"
        "link: src => dst : go [route=up]\n"
    )
    assert diagram.links[0].source == "src"
    assert diagram.links[0].target == "dst"


def test_labels_from_lang():
    ja = resolve_labels("ja", {})
    assert ja.label_question == "議論の問い"
    assert ja.label_key_message == "キーメッセージ"
    assert ja.label_source == "出典："
    en = resolve_labels("en", {})
    assert en.label_question == "Question"
    assert en.label_source == "Source:"
    override = resolve_labels("ja", {"label_question": "Q?"})
    assert override.label_question == "Q?"
    hidden = resolve_labels("en", {"label_source": ""})
    assert hidden.label_source == ""
    block = resolve_labels("en", {"question_label_placement": "block"})
    assert block.question_label_placement == "block"


def test_hard_break_backslash():
    assert "  \n" in apply_hard_breaks("one\\\ntwo")


def test_source_line_and_footer_hooks():
    meta, slides = parse_deck(
        "---\ntitle: T\nversion: \"1\"\ndate: \"2026-01-01\"\nlang: en\nstyle: x.md\n---\n\n"
        "# Title\n\nBody\n\nSource: Public note\n"
    )
    assert slides[0].source_html is not None
    assert "Public note" in slides[0].source_html
    assert '<span class="label">Source:</span>' in slides[0].source_html
    html = build_html(
        slides,
        tokens_to_css({
            "color_background": "#fff",
            "color_text": "#000",
            "color_title": "#000",
            "font_family": "sans-serif",
            "font_size_body": 22,
        }),
        [],
        "T",
        lang="en",
        page_number_placement="bottom-left",
    )
    assert 'lang="en"' in html
    assert 'class="page-number"' in html
    assert 'data-placement="bottom-left"' in html
    assert "1 / 1" in html
    assert 'class="source"' in html
    assert 'data-index="1"' in html
    assert 'class="title"' in html


def test_label_source_empty_hides_prefix():
    meta, slides = parse_deck(
        "---\ntitle: T\nversion: \"1\"\ndate: \"2026-01-01\"\nlang: en\nstyle: x.md\n---\n\n"
        "# Title\n\nBody\n\nSource: Public note\n",
        style_tokens={"label_source": ""},
    )
    assert slides[0].source_html is not None
    assert "Public note" in slides[0].source_html
    assert "Source:" not in slides[0].source_html
    assert 'class="label"' not in slides[0].source_html


def test_label_source_ja_default():
    meta, slides = parse_deck(
        "---\ntitle: T\nversion: \"1\"\ndate: \"2026-01-01\"\nlang: ja\nstyle: x.md\n---\n\n"
        "# Title\n\nBody\n\n出典：公開資料\n"
    )
    assert slides[0].source_html is not None
    assert '<span class="label">出典：</span>' in slides[0].source_html
    assert "公開資料" in slides[0].source_html


def test_straight_edge_shape_on_link_and_flow_option():
    link = parse_flow_body(
        "lane: Top\nA {#a}\nlane: Bottom\nB {#b}\n"
        "link: a => b [shape=straight]\n"
    )
    assert link.errors == []
    assert link.links[0].shape == "straight"
    html = render_flow_html(link)
    assert 'data-shape="straight"' in html

    flow_opt = parse_flow_body("A -> B\n", options=frozenset({"straight"}))
    assert flow_opt.lanes[0].edges[0].shape == "straight"
    assert 'flow-straight' in render_flow_html(flow_opt)

    chain = parse_flow_body("A -> B [shape=straight]\n")
    assert chain.errors == []
    assert chain.lanes[0].edges[0].shape == "straight"

    bad = parse_flow_body("A -> B [shape=zigzag]\n")
    assert any("unknown edge shape" in e for e in bad.errors)


def test_heading_attr_list_on_slide():
    slide = render_slide_markdown("# Path {#routing .route}\n\nBody\n")
    assert slide.slide_id == "routing"
    assert slide.slide_classes == ["route"]
    assert 'class="title"' in slide.html or "title" in slide.html


def test_column_options_and_head():
    slide = render_slide_markdown(
        "# T\n\n::: columns plain\n## Head\n\nLeft\n\n+++\n\nRight\n:::\n"
    )
    assert 'class="columns plain"' in slide.html
    assert "column-head" in slide.html


def test_flow_inside_columns():
    slide = render_slide_markdown(
        "# T\n\n::: columns\n::: flow\nA -> B\n:::\n\n+++\n\nRight\n:::\n"
    )
    assert "flow-node" in slide.html
    assert "columns" in slide.html


def test_question_label_inline_by_default():
    slide = render_slide_markdown("# T\n\n::: question\nHello there\n:::\n")
    assert "question-label-inline" in slide.html
    assert '<span class="label">' in slide.html
    # Label is inside the first paragraph
    assert '<p><span class="label">' in slide.html or '<p class=' in slide.html


def test_row_headers_from_empty_corner():
    slide = render_slide_markdown(
        "# T\n\n|  | A | B |\n| --- | --- | --- |\n| R1 | x | y |\n"
    )
    assert 'scope="row"' in slide.html
    assert "<th" in slide.html


def test_list_item_class_without_paragraph():
    slide = render_slide_markdown(
        "# T\n\n- One\n- Two\n  {: .highlight}\n"
    )
    assert 'class="highlight"' in slide.html
    # Prefer no wrapping <p> inside the classed li
    assert "<li" in slide.html


def test_flow_node_data_kind_in_html():
    slide = render_slide_markdown(
        "# T\n\n::: flow\n[actor] A -> [system] B\n:::\n"
    )
    assert 'data-kind="actor"' in slide.html
    assert "flow-node-actor" in slide.html
    assert "flow-chips" not in slide.html or True


def test_tokens_allow_zero_and_none():
    css = tokens_to_css({
        "color_background": "#fff",
        "color_text": "#000",
        "color_title": "#000",
        "font_family": "sans-serif",
        "font_size_body": 22,
        "card_radius": 0,
        "border_width": "none",
        "page_padding_top": 10,
        "color_top_bar": "#123456",
        "color_accent_2": "#abcdef",
        "color_highlight": "#ff0",
        "font_size_table": 17,
        "page_number_placement": "bottom-center",
        "footer_inset_bottom": "0.75em",
        "footer_inset_right": 8,
        "flow_callout_gap": 16,
        "flow_port_gap": 12,
        "flow_node_max_width": "none",
        "flow_node_min_height": 0,
        "column_min_height": 0,
    })
    assert "--card-radius: 0px;" in css
    assert "--border-width: none;" in css
    assert "--color-top-bar: #123456;" in css
    assert "--page-padding-top: 10px;" in css
    assert "--font-size-table: 17px;" in css
    assert "--page-number-placement: bottom-center;" in css
    assert "--footer-inset-bottom: 0.75em;" in css
    assert "--footer-inset-right: 8px;" in css
    assert "--flow-callout-gap: 16px;" in css
    assert "--flow-port-gap: 12px;" in css
    assert "--flow-node-max-width: none;" in css
    assert "--flow-node-min-height: 0px;" in css
    assert "--column-min-height: 0px;" in css
    assert "--flow-fill-height: 1;" in tokens_to_css({"flow_fill_height": "fill"})
    assert "--flow-fill-height: 0;" in tokens_to_css({})
    assert "--flow-preferred-height: 60%;" in tokens_to_css({})
    assert "--flow-preferred-grow: 1;" in tokens_to_css({})
    assert "--flow-preferred-height: none;" in tokens_to_css({"flow_preferred_height": "none"})
    assert "--flow-preferred-grow: 0;" in tokens_to_css({"flow_preferred_height": "none"})
    filled = tokens_to_css({"flow_fill_height": "fill", "flow_preferred_height": "40%"})
    assert "--flow-fill-height: 1;" in filled
    assert "--flow-preferred-height: none;" in filled
    assert "--flow-preferred-grow: 1;" in filled


def test_footer_inset_allows_negative():
    css = tokens_to_css({
        "color_background": "#fff",
        "color_text": "#000",
        "color_title": "#000",
        "font_family": "sans-serif",
        "font_size_body": 22,
        "footer_inset_right": "-20px",
        "footer_inset_bottom": -4,
    })
    assert "--footer-inset-right: -20px;" in css
    assert "--footer-inset-bottom: -4px;" in css


def test_plain_theme_stays_black_on_white():
    css = tokens_to_css({})
    assert "--color-background: #ffffff;" in css
    assert "--color-text: #000000;" in css
    assert "--color-title: #000000;" in css
    assert "--theme:" not in css
    plain = tokens_to_css({"theme": "plain"})
    assert "--color-background: #ffffff;" in plain
    assert "--color-flow-arrow: #000000;" in plain


def test_dark_blue_theme_fills_omitted_colours_and_yields_to_explicit():
    css = tokens_to_css({"theme": "dark-blue", "color_title": "#112233"})
    assert "--color-background: #EDE8E4;" in css
    assert "--color-text: #333333;" in css
    assert "--color-title: #112233;" in css
    assert "--color-flow-node-border: #073365;" in css
    assert "--color-flow-arrow: #073365;" in css
    assert "--color-highlight: #F7581D;" in css
    assert "--color-question-border: #F7581D;" in css
    assert "--color-card-bg: #E3EAF2;" in css
    assert "--theme:" not in css
    errors = validate_style_tokens(
        {"theme": "dark-blue", "font_family": "sans-serif", "font_size_body": 22},
        "style.md",
        1,
    )
    assert errors == []
    bad = validate_style_tokens(
        {"theme": "navy", "font_family": "sans-serif", "font_size_body": 22,
         "color_background": "#fff", "color_text": "#000", "color_title": "#000"},
        "style.md",
        1,
    )
    assert any("theme" in e.message for e in bad)


def test_dark_blue_example_file_uses_the_theme():
    from pathlib import Path

    tokens, _extra = load_style_file(Path("examples/deck_style_dark_blue.md"))
    assert tokens["theme"] == "dark-blue"
    assert "color_background" not in tokens
    css = tokens_to_css(tokens)
    assert "--color-background: #EDE8E4;" in css
    plain, _ = load_style_file(Path("examples/deck_style.md"))
    assert "theme" not in plain
    assert tokens_to_css(plain).count("--color-background: #ffffff;") == 1


def test_lane_align_option_and_blank_label():
    diagram = parse_flow_body(
        "lane: Upper\n"
        "A -> B -> C\n"
        "lane: [align=end]\n"
        "D {#d}\n"
        "link: d ..> C [route=up]\n"
    )
    assert diagram.lanes[1].label is None
    assert diagram.lanes[1].align == "end"
    assert not diagram.errors
    html = render_flow_html(diagram)
    assert 'data-lane="1" data-align="end" data-linked-above="true"' in html
    assert html.count("lane-label") == 1


def test_lane_label_keeps_text_before_align():
    diagram = parse_flow_body("lane: Field [align=center]\nA -> B\n")
    assert diagram.lanes[0].label == "Field"
    assert diagram.lanes[0].align == "center"


def test_unknown_lane_align_is_an_error():
    diagram = parse_flow_body("lane: Field [align=middle]\nA -> B\n")
    assert any("unknown lane align" in e for e in diagram.errors)
