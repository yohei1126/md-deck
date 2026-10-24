"""Unit tests for md-deck check (no Chromium)."""

from __future__ import annotations

from pathlib import Path

import pytest

from md_deck.cli import main
from md_deck.validate import check_deck

FIX = Path(__file__).parent / "fixtures"
GOOD = FIX / "good"
BAD = FIX / "bad"
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample.md"


def _messages(errors) -> list[str]:
    return [e.message for e in errors]


def test_good_fixture_passes():
    errors = check_deck(GOOD / "slides.md")
    assert errors == []


def test_example_sample_passes():
    errors = check_deck(EXAMPLE)
    assert errors == [], format_errs(errors)


def format_errs(errors):
    return "\n".join(e.format() for e in errors)


@pytest.mark.parametrize(
    ("folder", "needle"),
    [
        ("missing_fm_keys", "front matter"),
        ("unknown_slides_key", "unknown slides front matter key"),
        ("bad_date", "date"),
        ("missing_h1", "missing an H1"),
        ("two_h1", "more than one H1"),
        ("two_key_messages", "more than one Key Message"),
        ("unclosed_block", "unclosed"),
        ("unknown_block", "unknown block kind"),
        ("malformed_fence", "malformed fence"),
        ("nested_blocks", "nested blocks"),
        ("bad_flow", "empty flow node"),
        ("single_flow_node", "at least two nodes"),
        ("plus_outside", "+++ column separator"),
        ("empty_question", "question block is empty"),
        ("empty_slide_trailing", "empty"),
        ("skipped_heading", "heading level skipped"),
        ("h1_in_block", "H1 is not allowed inside"),
        ("bad_table", "columns"),
        ("raw_html", "raw HTML"),
        ("unclosed_code", "unclosed fenced code"),
        ("missing_asset", "does not exist"),
        ("absolute_path", "absolute local path"),
        ("stray_closer", "stray closing"),
        ("bad_style", "unknown style token"),
        ("unknown_flow_option", "unknown option"),
        ("unknown_node_kind", "unknown flow node kind"),
        ("unknown_column_option", "unknown option"),
        ("bad_negative_radius", "invalid size"),
    ],
)
def test_bad_fixtures_fail_with_needle(folder: str, needle: str):
    errors = check_deck(BAD / folder / "slides.md")
    assert errors, f"expected errors for {folder}"
    blob = "\n".join(_messages(errors))
    assert needle.lower() in blob.lower(), blob


def test_bad_style_reports_colour_and_missing_required():
    errors = check_deck(BAD / "bad_style" / "slides.md")
    msgs = "\n".join(_messages(errors))
    assert "unknown style token" in msgs
    assert "invalid CSS colour" in msgs or "colour" in msgs.lower()
    assert "missing required style token" in msgs or "color_title" in msgs


def test_cli_style_overrides_front_matter(tmp_path: Path):
    # Point style at good style via --style even if front matter wrong path
    slides = tmp_path / "slides.md"
    style = GOOD / "deck_style.md"
    slides.write_text(
        "---\n"
        "title: X\nversion: \"1\"\ndate: \"2026-01-01\"\nlang: en\n"
        "style: missing.md\n"
        "---\n\n# Title\n",
        encoding="utf-8",
    )
    # without override: missing style file
    assert any("not found" in e.message for e in check_deck(slides))
    # with override
    assert check_deck(slides, style) == []


def test_allow_html_flag():
    errors = check_deck(BAD / "raw_html" / "slides.md", allow_html=True)
    assert not any("raw HTML" in e.message for e in errors)


def test_cli_check_example_exit_zero():
    assert main(["check", str(EXAMPLE)]) == 0


def test_cli_check_bad_exit_one():
    assert main(["check", str(BAD / "missing_h1" / "slides.md")]) == 1


def test_error_format_is_file_line_message():
    errors = check_deck(BAD / "missing_h1" / "slides.md")
    formatted = errors[0].format()
    assert ": " in formatted
    # path:line: message
    parts = formatted.split(":", 2)
    assert len(parts) == 3
    assert parts[1].strip().isdigit()


def test_reports_all_errors_not_just_first():
    # two_h1 has missing... actually two H1 produces multiple; use a file with several issues
    text = (BAD / "two_key_messages" / "slides.md").read_text(encoding="utf-8")
    # Also add raw html by using nested bad - combine via tmp
    # bad_flow has empty node; ensure multiple errors from malformed multi-issue fixture
    errors = check_deck(BAD / "bad_flow" / "slides.md")
    # empty node + still has A and B so maybe only empty node; single_flow has one error
    errors2 = check_deck(BAD / "bad_style" / "slides.md")
    assert len(errors2) >= 2
