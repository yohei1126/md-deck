"""Parse slide Markdown into HTML fragments."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import markdown as md
import yaml

from md_deck.flow import parse_flow_body, render_flow_html

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
FENCE_BLOCK_RE = re.compile(
    r"::: *(?P<kind>question|flow|columns|source)"
    r"(?P<options>[^\n]*)\n(?P<body>.*?)\n:::",
    re.DOTALL | re.IGNORECASE,
)
KEY_MESSAGE_RE = re.compile(
    r"^\s*\*\*Key Message:\*\*\s*(?P<body>.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
SOURCE_LINE_RE = re.compile(
    r"^(?:Source|出典)\s*[:：]\s*(?P<body>.+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
H1_LINE_RE = re.compile(r"^#\s+(?P<title>.+?)(?:\s*\{(?P<attrs>[^}]*)\})?\s*$", re.M)

BLOCK_OPTIONS: dict[str, frozenset[str]] = {
    "question": frozenset(),
    "source": frozenset(),
    "flow": frozenset({"wide"}),
    "columns": frozenset({"plain", "panel"}),
}

DEFAULT_LABELS = {
    "ja": {"label_question": "議論の問い", "label_key_message": "キーメッセージ"},
    "en": {"label_question": "Question", "label_key_message": "Key Message"},
}


@dataclass
class RenderContext:
    label_question: str = "Question"
    label_key_message: str = "Key Message"


@dataclass
class SlideRender:
    html: str
    source_html: str | None = None
    slide_id: str | None = None
    slide_classes: list[str] | None = None


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    data = yaml.safe_load(match.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError("Slide front matter must be a YAML mapping.")
    return data, text[match.end() :]


def split_slides(body: str) -> list[str]:
    """Split on a line that is exactly --- (CommonMark thematic break used as separator)."""
    parts = re.split(r"\n---\n", body.strip())
    return [p.strip() for p in parts if p.strip()]


def resolve_labels(
    lang: str | None,
    style_tokens: dict[str, Any] | None = None,
) -> RenderContext:
    tokens = style_tokens or {}
    base = "ja" if (lang or "").lower().startswith("ja") else "en"
    defaults = DEFAULT_LABELS.get(base, DEFAULT_LABELS["en"])
    question = tokens.get("label_question")
    key = tokens.get("label_key_message")
    return RenderContext(
        label_question=str(question) if question is not None else defaults["label_question"],
        label_key_message=(
            str(key) if key is not None else defaults["label_key_message"]
        ),
    )


def apply_hard_breaks(text: str) -> str:
    """Convert trailing backslash (CommonMark-style) into a Markdown hard break."""
    # "foo\\" + newline -> "foo  " + newline (two trailing spaces = hard break)
    return re.sub(r"\\\s*\n", "  \n", text)


def block_newlines_to_breaks(text: str) -> str:
    """Inside question/source blocks, single newlines become hard breaks.

    Blank lines still separate paragraphs. Trailing backslash is also honoured
    via apply_hard_breaks afterwards.
    """
    text = apply_hard_breaks(text)
    parts = re.split(r"\n\s*\n", text.strip())
    rendered: list[str] = []
    for part in parts:
        lines = [ln.rstrip() for ln in part.split("\n")]
        rendered.append("  \n".join(lines))
    return "\n\n".join(rendered)


def _render_md(text: str) -> str:
    """Markdown with attr_list and backslash hard breaks only (no nl2br)."""
    text = apply_hard_breaks(text)
    return md.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "smarty", "attr_list"],
        output_format="html5",
    )


def _inline_md(text: str) -> str:
    """Render a single-line fragment to HTML without wrapping <p>."""
    rendered = _render_md(text).strip()
    if rendered.startswith("<p>") and rendered.endswith("</p>"):
        rendered = rendered[3:-4]
    return rendered


def _parse_options(kind: str, options_raw: str) -> tuple[frozenset[str], list[str]]:
    errors: list[str] = []
    tokens = [t for t in re.split(r"[\s|,]+", options_raw.strip()) if t]
    allowed = BLOCK_OPTIONS.get(kind, frozenset())
    opts: set[str] = set()
    for token in tokens:
        lower = token.lower()
        if lower not in allowed:
            errors.append(lower)
        else:
            opts.add(lower)
    return frozenset(opts), errors


def _render_question(body: str, ctx: RenderContext) -> str:
    # Skip apply_hard_breaks inside _render_md by pre-normalising newlines.
    inner = md.markdown(
        block_newlines_to_breaks(body),
        extensions=["tables", "fenced_code", "sane_lists", "smarty", "attr_list"],
        output_format="html5",
    )
    return (
        f'<aside class="question">'
        f'<span class="label">{_escape(ctx.label_question)}</span>'
        f"{inner}"
        f"</aside>"
    )


def _render_source_block(body: str) -> str:
    return md.markdown(
        block_newlines_to_breaks(body),
        extensions=["tables", "fenced_code", "sane_lists", "smarty", "attr_list"],
        output_format="html5",
    )


def _render_flow(body: str, options: frozenset[str]) -> str:
    diagram = parse_flow_body(body, options)
    return render_flow_html(diagram)


def _mark_column_head(col_html: str) -> str:
    """Add .column-head to the first heading in a column, if any."""
    return re.sub(
        r"(<(?:h[2-6]))(\b[^>]*)(>)",
        lambda m: (
            m.group(1)
            + _merge_class_attr(m.group(2), "column-head")
            + m.group(3)
        ),
        col_html,
        count=1,
        flags=re.IGNORECASE,
    )


def _merge_class_attr(attrs: str, extra: str) -> str:
    match = re.search(r'\bclass="([^"]*)"', attrs)
    if match:
        classes = match.group(1).split()
        if extra not in classes:
            classes.append(extra)
        return (
            attrs[: match.start()]
            + f'class="{" ".join(classes)}"'
            + attrs[match.end() :]
        )
    return f'{attrs} class="{extra}"' if attrs else f' class="{extra}"'


def _render_columns(body: str, options: frozenset[str]) -> str:
    cols = [c.strip() for c in re.split(r"\n\+\+\+\n", body.strip())]
    option_classes = " ".join(sorted(options))
    class_attr = "columns" + (f" {option_classes}" if option_classes else "")
    parts = [f'<div class="{class_attr}">']
    for col in cols:
        inner = _mark_column_head(_render_md(col))
        parts.append(f'<div class="column">{inner}</div>')
    parts.append("</div>")
    return "\n".join(parts)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_key_messages(text: str, ctx: RenderContext) -> str:
    def repl(match: re.Match[str]) -> str:
        body = match.group("body").strip()
        return (
            '<div class="key-message">'
            f'<span class="label">{_escape(ctx.label_key_message)}</span> '
            f"{_inline_md(body)}"
            "</div>"
        )

    return KEY_MESSAGE_RE.sub(repl, text)


def _extract_heading_attrs(slide_md: str) -> tuple[str, str | None, list[str]]:
    """Return (slide_md, optional id, classes) from the first H1 attr_list."""
    slide_id: str | None = None
    classes: list[str] = []

    def repl(match: re.Match[str]) -> str:
        nonlocal slide_id, classes
        attrs = match.group("attrs")
        for token in attrs.split():
            if token.startswith("#"):
                slide_id = token[1:] or slide_id
            elif token.startswith("."):
                name = token[1:]
                if name and name not in classes:
                    classes.append(name)
        # Keep attr_list on the heading so the <h1> also gets id/class.
        return match.group(0)

    # Only rewrite first H1 occurrence for extraction; leave syntax for attr_list.
    match = H1_LINE_RE.search(slide_md)
    if match and match.group("attrs"):
        for token in match.group("attrs").split():
            if token.startswith("#") and len(token) > 1:
                slide_id = token[1:]
            elif token.startswith(".") and len(token) > 1:
                classes.append(token[1:])
    return slide_md, slide_id, classes


def _add_title_class(html: str) -> str:
    """Ensure the first <h1> has class title."""

    def repl(match: re.Match[str]) -> str:
        tag, attrs, rest = match.group(1), match.group(2), match.group(3)
        return f"{tag}{_merge_class_attr(attrs, 'title')}{rest}"

    return re.sub(r"(<h1)([^>]*)(>)", repl, html, count=1, flags=re.IGNORECASE)


def _extract_sources(text: str) -> tuple[str, str | None]:
    """Pull Source:/出典: lines and leave the rest. Returns (body, source_html)."""
    sources: list[str] = []

    def repl_line(match: re.Match[str]) -> str:
        sources.append(match.group("body").strip())
        return ""

    body = SOURCE_LINE_RE.sub(repl_line, text)
    if not sources:
        return body, None
    # Join multiple source lines with spaces; render as inline markdown fragments.
    joined = " ".join(sources)
    return body, _inline_md(joined)


def render_slide_markdown(
    slide_md: str,
    ctx: RenderContext | None = None,
) -> SlideRender:
    ctx = ctx or RenderContext()
    slide_md, slide_id, slide_classes = _extract_heading_attrs(slide_md)
    slide_md, source_from_line = _extract_sources(slide_md)
    text = _render_key_messages(slide_md, ctx)

    chunks: list[str] = []
    source_parts: list[str] = []
    if source_from_line:
        source_parts.append(source_from_line)

    pos = 0
    for match in FENCE_BLOCK_RE.finditer(text):
        before = text[pos : match.start()]
        if before.strip():
            chunks.append(_render_md(before))
        kind = match.group("kind").lower()
        options_raw = match.group("options") or ""
        options, _unknown = _parse_options(kind, options_raw)
        body = match.group("body")
        if kind == "question":
            chunks.append(_render_question(body, ctx))
        elif kind == "flow":
            chunks.append(_render_flow(body, options))
        elif kind == "columns":
            chunks.append(_render_columns(body, options))
        elif kind == "source":
            source_parts.append(_render_source_block(body))
        pos = match.end()
    after = text[pos:]
    if after.strip():
        chunks.append(_render_md(after))

    html = _add_title_class("\n".join(chunks))
    source_html = None
    if source_parts:
        # Prefer plain text joined; source blocks may include <p>
        source_html = "\n".join(source_parts)
    return SlideRender(
        html=html,
        source_html=source_html,
        slide_id=slide_id,
        slide_classes=slide_classes or None,
    )


def parse_deck(
    text: str,
    style_tokens: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[SlideRender]]:
    meta, body = split_front_matter(text)
    ctx = resolve_labels(str(meta.get("lang") or ""), style_tokens)
    slides = [render_slide_markdown(s, ctx) for s in split_slides(body)]
    if not slides:
        raise ValueError("No slides found. Separate slides with a --- line.")
    return meta, slides
