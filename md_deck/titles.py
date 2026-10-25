"""Cover-title line breaks: explicit ``\\n`` in an H1, plus a width estimate.

ATX headings are a single line, so a trailing backslash does not continue a
title. Authors write ``\\n`` inside the heading (the same marker flow labels
use). The renderer turns that into ``<br>``. ``md-deck check`` rejects empty
or over-long breaks on every title, and on cover titles it also rejects
mid-phrase breaks, unbalanced lines, and CJK titles that would wrap on their
own. Keep the thresholds aligned with ``docs/VISUAL_POLICY.md``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

# Matches one ATX H1 line, including an optional attr_list.
H1_LINE_RE = re.compile(
    r"^#\s+(?P<title>.+?)(?:\s*\{(?P<attrs>[^}]*)\})?\s*$",
    re.M,
)

# Private-use sentinel so Markdown does not eat the break marker.
TITLE_BREAK_SENTINEL = "\uE000"

MAX_TITLE_LINES = 3
# Display units: a wide (CJK) character counts as 2, a Latin character as 1.
MIN_LINE_UNITS = 4
MIN_BALANCE_RATIO = 0.45
# Estimated width / content box. Slack absorbs the Latin-width heuristic.
CJK_WRAP_RATIO = 1.02
MULTI_WRAP_RATIO = 2.05

_FUNCTION_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "to",
        "and",
        "or",
        "for",
        "in",
        "on",
        "with",
        "by",
        "at",
        "from",
        "as",
        "vs",
        "via",
        "into",
        "over",
        "than",
        "that",
        "this",
        "nor",
        "but",
    }
)
# A whole line that is only a particle is a mid-phrase break.
_PARTICLES = frozenset(
    {
        "は",
        "が",
        "を",
        "に",
        "で",
        "と",
        "も",
        "の",
        "へ",
        "や",
        "から",
        "まで",
        "より",
        "ね",
        "よ",
        "か",
    }
)
_OPENERS = frozenset("（「『【〔［(")
_CLOSERS = frozenset("）」』】〕］)、。，．,.!?;；:：")
# A continuation line that begins with one of these is usually a mid-phrase break.
# `への` / `との` / `での` stay quiet: the particle is tied to の.
_LEADING_PARTICLE_RE = re.compile(r"^(?P<p>[へをとのにでがはもや])(?!の)")


@dataclass(frozen=True)
class TitleMeasure:
    """Content-box width and title font size, in px. None skips the wrap estimate."""

    content_width_px: float | None
    font_size_px: float | None


def classes_from_attrs(attrs: str | None) -> list[str]:
    if not attrs:
        return []
    classes: list[str] = []
    for token in attrs.split():
        if token.startswith(".") and len(token) > 1:
            classes.append(token[1:])
    return classes


def is_cover_slide(index: int, classes: list[str] | None) -> bool:
    """First slide, or any slide whose H1 carries ``.cover``.

    ``.no-cover`` opts the first slide out. ``.cover`` wins if both are set.
    """
    names = set(classes or [])
    if "cover" in names:
        return True
    if index == 1 and "no-cover" not in names:
        return True
    return False


def encode_h1_breaks(slide_md: str) -> str:
    """Replace ``\\n`` inside H1 text with a sentinel the renderer turns into ``<br>``."""

    def repl(match: re.Match[str]) -> str:
        title = match.group("title").replace("\\n", TITLE_BREAK_SENTINEL)
        attrs = match.group("attrs")
        if attrs:
            return f"# {title} {{{attrs}}}"
        return f"# {title}"

    # Only the first H1 is the slide title. Later `#` lines may be code samples.
    return H1_LINE_RE.sub(repl, slide_md, count=1)


def display_units(text: str) -> int:
    total = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in {"W", "F"}:
            total += 2
        else:
            total += 1
    return total


def contains_cjk(text: str) -> bool:
    for ch in text:
        if unicodedata.east_asian_width(ch) in {"W", "F"}:
            return True
        code = ord(ch)
        if 0x3040 <= code <= 0x30FF or 0x31F0 <= code <= 0x31FF:
            return True
    return False


def estimated_width_px(text: str, font_px: float) -> float:
    width = 0.0
    for ch in text:
        if ch.isspace():
            width += font_px * 0.33
        elif unicodedata.east_asian_width(ch) in {"W", "F"}:
            width += font_px
        else:
            width += font_px * 0.56
    return width


def _length_px(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    match = re.fullmatch(r"(-?[0-9]+(?:\.[0-9]+)?)(px)?", text)
    if not match:
        return None
    return float(match.group(1))


def title_measure_from_tokens(tokens: dict[str, Any] | None) -> TitleMeasure:
    """Approximate the title's content box from style tokens (plain defaults)."""
    data = tokens or {}

    def pick(key: str, default: float) -> float | None:
        if key in data:
            return _length_px(data[key])
        return default

    font = pick("font_size_title", 36.0)
    page_w = pick("page_width", 1280.0)

    def side(key: str) -> float | None:
        if key in data:
            return _length_px(data[key])
        if "page_padding" in data:
            return _length_px(data["page_padding"])
        return 48.0

    left = side("page_padding_left")
    right = side("page_padding_right")
    if (
        font is None
        or page_w is None
        or left is None
        or right is None
        or font <= 0
        or page_w <= 0
    ):
        return TitleMeasure(None, font if font and font > 0 else None)
    content = page_w - left - right
    if content <= 0:
        return TitleMeasure(None, font)
    return TitleMeasure(content, font)


def _breaks_phrase(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped[-1] in _OPENERS or stripped[0] in _CLOSERS:
        return True
    if all(unicodedata.category(ch).startswith("P") or ch.isspace() for ch in stripped):
        return True
    core = stripped.strip("".join(_OPENERS | _CLOSERS)).strip()
    if not core:
        return True
    if core.lower() in _FUNCTION_WORDS or core in _PARTICLES:
        return True
    return False


def title_break_issues(
    title: str,
    *,
    cover: bool,
    measure: TitleMeasure,
    implicit_cover: bool = False,
) -> list[tuple[str, bool]]:
    """Return ``(message, warning)`` problems. ``warning`` does not fail the build."""
    if "\\n" not in title and not cover:
        return []

    lines = [part.strip() for part in title.split("\\n")]
    label = "cover title" if cover else "title"
    issues: list[tuple[str, bool]] = []
    if any(not line for line in lines):
        issues.append(
            (
                f"{label} has an empty line around \\n; break only between phrases",
                False,
            )
        )
        return issues
    if len(lines) > MAX_TITLE_LINES:
        issues.append(
            (
                f"{label} has more than {MAX_TITLE_LINES} lines; "
                "keep one phrase per line",
                False,
            )
        )

    if not cover or len(lines) < 2:
        if cover and len(lines) == 1:
            _append_wrap_issue(lines[0], measure, issues, implicit_cover)
        return issues

    for index, line in enumerate(lines):
        if _breaks_phrase(line):
            issues.append(
                (
                    "cover title breaks inside a phrase "
                    f"({line!r}); put \\n at a phrase boundary",
                    False,
                )
            )
        elif index >= 1:
            lead = _LEADING_PARTICLE_RE.match(line)
            if lead:
                particle = lead.group("p")
                issues.append(
                    (
                        "cover title line "
                        f"{index + 1} starts with the particle {particle!r}; "
                        "keep that particle on the previous line",
                        True,
                    )
                )
    units = [display_units(line) for line in lines]
    short, long = min(units), max(units)
    if long == 0 or short < MIN_LINE_UNITS or short / long < MIN_BALANCE_RATIO:
        issues.append(
            (
                "cover title lines are unbalanced; "
                "break so the shorter line is at least about half the longer one",
                False,
            )
        )
    return issues


def _no_cover_hint(implicit_cover: bool) -> str:
    if not implicit_cover:
        return ""
    return " If this slide is not a cover, add {.no-cover} to the H1."


def _append_wrap_issue(
    text: str,
    measure: TitleMeasure,
    issues: list[tuple[str, bool]],
    implicit_cover: bool,
) -> None:
    if measure.content_width_px is None or measure.font_size_px is None:
        return
    width = estimated_width_px(text, measure.font_size_px)
    content = measure.content_width_px
    hint = _no_cover_hint(implicit_cover)
    if contains_cjk(text) and width > content * CJK_WRAP_RATIO:
        issues.append(
            (
                "cover title will wrap mid-phrase; insert \\n at a phrase boundary "
                "and keep the lines similar in length."
                + hint,
                False,
            )
        )
        return
    if width > content * MULTI_WRAP_RATIO:
        issues.append(
            (
                "cover title will wrap to more than two lines; insert \\n so each "
                "line is a complete phrase of similar length."
                + hint,
                False,
            )
        )


def heading_title_messages(
    line: str,
    slide_index: int,
    measure: TitleMeasure,
) -> list[tuple[str, bool]]:
    match = H1_LINE_RE.match(line.strip())
    if not match:
        return []
    classes = classes_from_attrs(match.group("attrs"))
    cover = is_cover_slide(slide_index, classes)
    implicit = cover and "cover" not in classes
    return title_break_issues(
        match.group("title"),
        cover=cover,
        measure=measure,
        implicit_cover=implicit,
    )
