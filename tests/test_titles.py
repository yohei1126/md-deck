"""Cover-title breaks and the diagram-pattern example."""

from __future__ import annotations

import re
from pathlib import Path

from md_deck.build import build_html
from md_deck.flow import parse_flow_body
from md_deck.slides import SlideRender, render_slide_markdown
from md_deck.validate import check_deck

EXAMPLE = Path(__file__).resolve().parents[1] / "examples"


def _slides(tmp_path: Path, body: str, style_extra: str = "") -> Path:
    style = tmp_path / "deck_style.md"
    style.write_text(
        "---\n"
        'color_background: "#ffffff"\n'
        'color_text: "#000000"\n'
        'color_title: "#000000"\n'
        "font_family: sans-serif\n"
        "font_size_body: 22\n"
        f"{style_extra}"
        "---\n",
        encoding="utf-8",
    )
    slides = tmp_path / "slides.md"
    slides.write_text(
        "---\n"
        "title: T\n"
        'version: "1"\n'
        'date: "2026-01-01"\n'
        "lang: ja\n"
        "style: deck_style.md\n"
        "---\n\n"
        + body,
        encoding="utf-8",
    )
    return slides


def _messages(tmp_path: Path, body: str, style_extra: str = "") -> str:
    errors = check_deck(_slides(tmp_path, body, style_extra))
    return "\n".join(e.message for e in errors)


def test_h1_break_does_not_rewrite_a_later_code_sample():
    slide = render_slide_markdown("# Title\n\n```markdown\n# Foo\\nBar\n```\n")
    assert "<br>" not in slide.html
    assert "Foo\\nBar" in slide.html


def test_h1_newline_renders_as_break_and_keeps_attrs():
    slide = render_slide_markdown("# One\\nTwo {#cover .cover}\n\nBody\n")
    assert slide.slide_id == "cover"
    assert slide.slide_classes == ["cover"]
    assert "<h1" in slide.html
    assert "One<br>Two" in slide.html


def _cover_ids(html: str) -> list[str]:
    return re.findall(r'<section\b[^>]*\bid="([^"]+)"[^>]*\bdata-cover="true"', html)


def test_cover_attribute_follows_first_slide_and_classes():
    html = build_html(
        [
            SlideRender(html="<h1 class='title'>Hi</h1>", slide_classes=["intro"]),
            SlideRender(html="<h1 class='title'>Next</h1>"),
        ],
        "",
        [],
        "t",
    )
    assert _cover_ids(html) == ["slide-1"]

    opted_out = build_html(
        [
            SlideRender(html="<h1 class='title'>Hi</h1>", slide_classes=["no-cover"]),
            SlideRender(html="<h1 class='title'>Next</h1>", slide_classes=["cover"]),
        ],
        "",
        [],
        "t",
    )
    assert _cover_ids(opted_out) == ["slide-2"]


def test_short_latin_cover_passes(tmp_path: Path):
    assert _messages(tmp_path, "# Welcome to md-deck\n\nBody\n") == ""


def test_cjk_cover_without_break_fails(tmp_path: Path):
    body = "# " + ("見" * 40) + "\n\nBody\n"
    blob = _messages(tmp_path, body)
    assert "wrap mid-phrase" in blob


def test_cjk_cover_with_balanced_break_passes(tmp_path: Path):
    body = "# 骨子を先に見せる\\n色は抑えて残す\n\nBody\n"
    assert _messages(tmp_path, body) == ""


def test_unbalanced_cover_break_fails(tmp_path: Path):
    body = "# Go\\nThis is a much longer second line\n\nBody\n"
    blob = _messages(tmp_path, body)
    assert "unbalanced" in blob


def test_function_word_break_fails(tmp_path: Path):
    body = "# of\\ncourse this title continues onward\n\nBody\n"
    blob = _messages(tmp_path, body)
    assert "breaks inside a phrase" in blob


def test_particle_and_opener_breaks_fail(tmp_path: Path):
    particle = _messages(tmp_path, "# の\\n色は抑えて残す\n\nBody\n")
    assert "breaks inside a phrase" in particle
    opener = _messages(
        tmp_path,
        "# 方針の骨子を見せる（\\n色は抑えて残す\n\nBody\n",
    )
    assert "breaks inside a phrase" in opener


def test_no_cover_opts_out_of_cjk_rule(tmp_path: Path):
    body = "# " + ("見" * 40) + " {.no-cover}\n\nBody\n"
    assert _messages(tmp_path, body) == ""


def test_cover_class_on_later_slide(tmp_path: Path):
    body = (
        "# Short opener\n\nBody\n"
        "\n---\n\n"
        "# " + ("見" * 40) + " {.cover}\n\nMore\n"
    )
    blob = _messages(tmp_path, body)
    assert "wrap mid-phrase" in blob


def test_content_title_ignores_balance_but_limits_lines(tmp_path: Path):
    body = (
        "# Short opener {.no-cover}\n\nBody\n"
        "\n---\n\n"
        "# Go\\nThis is a much longer second line\n\nMore\n"
    )
    assert _messages(tmp_path, body) == ""
    too_many = (
        "# Short opener {.no-cover}\n\nBody\n"
        "\n---\n\n"
        "# One\\nTwo\\nThree\\nFour\n\nMore\n"
    )
    assert "more than 3 lines" in _messages(tmp_path, too_many)


def test_empty_break_fails(tmp_path: Path):
    body = "# One\\n\\nTwo\n\nBody\n"
    assert "empty line" in _messages(tmp_path, body)


def test_long_latin_cover_asks_for_breaks(tmp_path: Path):
    body = "# " + ("word " * 40) + "\n\nBody\n"
    blob = _messages(tmp_path, body)
    assert "more than two lines" in blob


def test_unknown_font_unit_skips_wrap_estimate(tmp_path: Path):
    body = "# " + ("見" * 40) + "\n\nBody\n"
    blob = _messages(tmp_path, body, 'font_size_title: "2rem"\n')
    assert blob == ""


def test_branch_recipe_fans_into_the_stack():
    diagram = parse_flow_body(
        "Start {#start}\n"
        "{ Keep / Change }\n"
        "{#start} -> Keep\n"
        "{#start} -> Change\n"
    )
    assert diagram.errors == []
    edges = [(e.source, e.target) for e in diagram.lanes[0].edges]
    assert ("start", "Keep") in edges
    assert ("start", "Change") in edges
    assert any(isinstance(col, list) for col in diagram.lanes[0].columns)


def test_diagram_pattern_examples_pass():
    errors = check_deck(EXAMPLE / "diagram_patterns.md")
    assert errors == [], "\n".join(e.format() for e in errors)
    for name in ("sample.md", "routing_demo.md"):
        found = check_deck(EXAMPLE / name)
        assert found == [], "\n".join(e.format() for e in found)
