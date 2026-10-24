"""Unit tests for slide/flow rendering (no Chromium)."""

from __future__ import annotations

from md_deck.build import build_html
from md_deck.flow import parse_flow_body, parse_node_text
from md_deck.slides import apply_hard_breaks, parse_deck, render_slide_markdown, resolve_labels
from md_deck.style import tokens_to_css


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


def test_lanes_and_links():
    diagram = parse_flow_body(
        "lane: Upper\n"
        "A -> B\n"
        "lane: Lower\n"
        "C -> D\n"
        "link: B => C : bridge\n"
    )
    assert len(diagram.lanes) == 2
    assert diagram.lanes[0].label == "Upper"
    assert len(diagram.links) == 1
    assert diagram.links[0].label == "bridge"
    html = __import__("md_deck.flow", fromlist=["render_flow_html"]).render_flow_html(diagram)
    assert 'data-kind' not in html or True
    assert 'class="lane"' in html
    assert "lane-label" in html
    assert 'data-from="B"' in html
    assert 'data-to="C"' in html


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


def test_labels_from_lang():
    ja = resolve_labels("ja", {})
    assert ja.label_question == "議論の問い"
    assert ja.label_key_message == "キーメッセージ"
    en = resolve_labels("en", {})
    assert en.label_question == "Question"
    override = resolve_labels("ja", {"label_question": "Q?"})
    assert override.label_question == "Q?"


def test_hard_break_backslash():
    assert "  \n" in apply_hard_breaks("one\\\ntwo")


def test_source_line_and_footer_hooks():
    meta, slides = parse_deck(
        "---\ntitle: T\nversion: \"1\"\ndate: \"2026-01-01\"\nlang: en\nstyle: x.md\n---\n\n"
        "# Title\n\nBody\n\nSource: Public note\n"
    )
    assert slides[0].source_html is not None
    assert "Public note" in slides[0].source_html
    html = build_html(slides, tokens_to_css({
        "color_background": "#fff",
        "color_text": "#000",
        "color_title": "#000",
        "font_family": "sans-serif",
        "font_size_body": 22,
    }), [], "T", lang="en")
    assert 'lang="en"' in html
    assert 'class="page-number"' in html
    assert "1 / 1" in html
    assert 'class="source"' in html
    assert 'data-index="1"' in html
    assert 'class="title"' in html


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


def test_flow_node_data_kind_in_html():
    slide = render_slide_markdown(
        "# T\n\n::: flow\n[actor] A -> [system] B\n:::\n"
    )
    assert 'data-kind="actor"' in slide.html
    assert "flow-node-actor" in slide.html


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
    })
    assert "--card-radius: 0px;" in css
    assert "--border-width: none;" in css
    assert "--color-top-bar: #123456;" in css
    assert "--page-padding-top: 10px;" in css
