"""Parse slide Markdown into HTML fragments."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import markdown as md
import yaml

from md_deck.flow import parse_flow_body, render_flow_html

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
FENCE_LINE_RE = re.compile(r"^(?P<colons>:{3,})\s*(?P<rest>.*)$")
KEY_MESSAGE_RE = re.compile(
    r"^\s*\*\*Key Message:\*\*\s*(?P<body>.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
SOURCE_LINE_RE = re.compile(
    r"^(?:Source|出典)\s*[:：]\s*(?P<body>.+)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
H1_LINE_RE = re.compile(r"^#\s+(?P<title>.+?)(?:\s*\{(?P<attrs>[^}]*)\})?\s*$", re.M)

# Only flow may nest inside columns. All other nesting stays forbidden.
ALLOWED_NESTING = frozenset({("columns", "flow")})

BLOCK_OPTIONS: dict[str, frozenset[str]] = {
    "question": frozenset(),
    "source": frozenset(),
    "flow": frozenset({"wide", "straight"}),
    "columns": frozenset({"plain", "panel"}),
}

DEFAULT_LABELS = {
    "ja": {
        "label_question": "議論の問い",
        "label_key_message": "キーメッセージ",
        "label_source": "出典：",
    },
    "en": {
        "label_question": "Question",
        "label_key_message": "Key Message",
        "label_source": "Source:",
    },
}


@dataclass
class RenderContext:
    label_question: str = "Question"
    label_key_message: str = "Key Message"
    label_source: str = "Source:"
    question_label_placement: str = "inline"  # inline | block


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
    # Empty string hides the source prefix; omit the token to use the lang default.
    source = tokens.get("label_source")
    placement = str(tokens.get("question_label_placement") or "inline").lower()
    if placement not in {"inline", "block"}:
        placement = "inline"
    return RenderContext(
        label_question=str(question) if question is not None else defaults["label_question"],
        label_key_message=(
            str(key) if key is not None else defaults["label_key_message"]
        ),
        label_source=(
            str(source) if source is not None else defaults["label_source"]
        ),
        question_label_placement=placement,
    )


def apply_hard_breaks(text: str) -> str:
    """Convert trailing backslash (CommonMark-style) into a Markdown hard break."""
    return re.sub(r"\\\s*\n", "  \n", text)


def block_newlines_to_breaks(text: str) -> str:
    """Inside question/source blocks, single newlines become hard breaks."""
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
    html = md.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "smarty", "attr_list"],
        output_format="html5",
    )
    html = _promote_row_headers(html)
    html = _unwrap_simple_list_item_paragraphs(html)
    return html


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


def _promote_row_headers(html: str) -> str:
    """When the first header cell is empty, promote the first body cell to th[scope=row]."""

    def repl_table(match: re.Match[str]) -> str:
        table = match.group(0)
        thead_cells = re.findall(r"<th\b[^>]*>(.*?)</th>", table, flags=re.I | re.S)
        if not thead_cells:
            return table
        first = re.sub(r"<[^>]+>", "", thead_cells[0]).strip()
        if first:
            return table

        def repl_row(row_match: re.Match[str]) -> str:
            row = row_match.group(0)
            # Skip header rows (already all <th>)
            if re.search(r"<td\b", row, flags=re.I) is None:
                return row
            return _swap_first_td(row)

        return re.sub(r"<tr\b[^>]*>.*?</tr>", repl_row, table, flags=re.I | re.S)

    return re.sub(r"<table\b[^>]*>.*?</table>", repl_table, html, flags=re.I | re.S)


def _swap_first_td(row: str) -> str:
    match = re.search(r"<td(\b[^>]*)>(.*?)</td>", row, flags=re.I | re.S)
    if not match:
        return row
    attrs = match.group(1)
    if re.search(r"\bscope\s*=", attrs, flags=re.I) is None:
        attrs = f'{attrs} scope="row"'
    replacement = f"<th{attrs}>{match.group(2)}</th>"
    return row[: match.start()] + replacement + row[match.end() :]

def _unwrap_simple_list_item_paragraphs(html: str) -> str:
    """Keep list-item classes on <li> without a wrapping <p> for simple items."""

    def repl(match: re.Match[str]) -> str:
        open_tag, inner, close = match.group(1), match.group(2), match.group(3)
        # Only unwrap when the paragraph has no nested block tags.
        if re.search(r"</?(ul|ol|table|pre|blockquote)\b", inner, flags=re.I):
            return match.group(0)
        return f"{open_tag}{inner}{close}"

    return re.sub(
        r"(<li\b[^>]*>)\s*<p>(.*?)</p>\s*(</li>)",
        repl,
        html,
        flags=re.I | re.S,
    )


def _render_question(body: str, ctx: RenderContext) -> str:
    inner = md.markdown(
        block_newlines_to_breaks(body),
        extensions=["tables", "fenced_code", "sane_lists", "smarty", "attr_list"],
        output_format="html5",
    )
    label = f'<span class="label">{_escape(ctx.label_question)}</span>'
    placement = ctx.question_label_placement
    aside_class = "question"
    if placement == "block":
        aside_class += " question-label-block"
        content = f"{label}{inner}"
    else:
        aside_class += " question-label-inline"
        # Put the label inline in the first paragraph.
        if re.match(r"<p\b", inner, flags=re.I):
            content = re.sub(
                r"<p(\b[^>]*)>",
                rf'<p\1>{label} ',
                inner,
                count=1,
                flags=re.I,
            )
        else:
            content = f"{label} {inner}"
    return f'<aside class="{aside_class}">{content}</aside>'


def _render_source_block(body: str) -> str:
    return md.markdown(
        block_newlines_to_breaks(body),
        extensions=["tables", "fenced_code", "sane_lists", "smarty", "attr_list"],
        output_format="html5",
    )


def _prefix_source_label(html: str, ctx: RenderContext) -> str:
    """Prepend label_source before footer source HTML; empty token hides it."""
    label = ctx.label_source
    if not label:
        return html
    # Fullwidth colon already closes the Japanese prefix; ASCII colon needs a space.
    sep = "" if label.endswith("：") else " "
    return f'<span class="label">{_escape(label)}</span>{sep}{html}'


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


def _render_fragment(text: str, ctx: RenderContext, *, parent: str | None = None) -> str:
    """Render Markdown that may contain ::: fences, with limited nesting."""
    chunks: list[str] = []
    source_parts: list[str] = []  # unused here; columns ignore source
    lines = text.splitlines(keepends=True)
    i = 0
    buf: list[str] = []

    def flush_buf() -> None:
        nonlocal buf
        if not buf:
            return
        chunk = "".join(buf)
        if chunk.strip():
            chunks.append(_render_md(chunk))
        buf = []

    while i < len(lines):
        line = lines[i]
        fence = FENCE_LINE_RE.match(line.rstrip("\n"))
        if fence and len(fence.group("colons")) == 3 and fence.group("rest").strip():
            rest = fence.group("rest").strip()
            tokens = rest.split()
            kind = tokens[0].lower() if tokens else ""
            options_raw = " ".join(tokens[1:])
            if kind in BLOCK_OPTIONS:
                if parent is not None and (parent, kind) not in ALLOWED_NESTING:
                    # Leave as literal text; validation catches illegal nesting.
                    buf.append(line)
                    i += 1
                    continue
                # Find matching closer with nesting awareness
                body_lines, next_i = _extract_fence_body(lines, i + 1)
                flush_buf()
                options, _unknown = _parse_options(kind, options_raw)
                body = "\n".join(body_lines)
                if kind == "question":
                    chunks.append(_render_question(body, ctx))
                elif kind == "flow":
                    chunks.append(_render_flow(body, options))
                elif kind == "columns":
                    chunks.append(_render_columns(body, options, ctx))
                elif kind == "source":
                    # Source blocks inside fragments (unusual) render as HTML
                    chunks.append(
                        f'<div class="source">{_render_source_block(body)}</div>'
                    )
                i = next_i
                continue
        buf.append(line)
        i += 1
    flush_buf()
    return "\n".join(chunks)


def _extract_fence_body(lines: list[str], start: int) -> tuple[list[str], int]:
    """Return body lines and index after the matching ::: closer."""
    depth = 1
    body: list[str] = []
    i = start
    while i < len(lines):
        raw = lines[i].rstrip("\n")
        fence = FENCE_LINE_RE.match(raw)
        if fence and len(fence.group("colons")) == 3:
            rest = fence.group("rest").strip()
            if rest == "":
                depth -= 1
                if depth == 0:
                    return body, i + 1
                body.append(lines[i].rstrip("\n"))
                i += 1
                continue
            # Nested opener
            depth += 1
            body.append(lines[i].rstrip("\n"))
            i += 1
            continue
        body.append(lines[i].rstrip("\n"))
        i += 1
    return body, i


def _render_columns(body: str, options: frozenset[str], ctx: RenderContext) -> str:
    cols = [c.strip() for c in re.split(r"\n\+\+\+\n", body.strip())]
    option_classes = " ".join(sorted(options))
    class_attr = "columns" + (f" {option_classes}" if option_classes else "")
    parts = [f'<div class="{class_attr}">']
    for col in cols:
        # Allow nested flow fences inside a column.
        inner = _mark_column_head(_render_fragment(col, ctx, parent="columns"))
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
        source_parts.append(_prefix_source_label(source_from_line, ctx))

    lines = text.splitlines(keepends=True)
    i = 0
    buf: list[str] = []

    def flush_buf() -> None:
        nonlocal buf
        if not buf:
            return
        chunk = "".join(buf)
        if chunk.strip():
            chunks.append(_render_md(chunk))
        buf = []

    while i < len(lines):
        line = lines[i]
        fence = FENCE_LINE_RE.match(line.rstrip("\n"))
        if fence and len(fence.group("colons")) == 3:
            rest = fence.group("rest").strip()
            if rest:
                tokens = rest.split()
                kind = tokens[0].lower() if tokens else ""
                options_raw = " ".join(tokens[1:])
                if kind in BLOCK_OPTIONS:
                    body_lines, next_i = _extract_fence_body(lines, i + 1)
                    flush_buf()
                    options, _unknown = _parse_options(kind, options_raw)
                    body = "\n".join(body_lines)
                    if kind == "question":
                        chunks.append(_render_question(body, ctx))
                    elif kind == "flow":
                        chunks.append(_render_flow(body, options))
                    elif kind == "columns":
                        chunks.append(_render_columns(body, options, ctx))
                    elif kind == "source":
                        source_parts.append(
                            _prefix_source_label(_render_source_block(body), ctx)
                        )
                    i = next_i
                    continue
        buf.append(line)
        i += 1
    flush_buf()

    html = _add_title_class("\n".join(chunks))
    source_html = None
    if source_parts:
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
