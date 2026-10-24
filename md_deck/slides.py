"""Parse slide Markdown into HTML fragments."""

from __future__ import annotations

import html
import re
from typing import Any

import markdown as md
import yaml

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
FENCE_BLOCK_RE = re.compile(
    r"::: *(?P<kind>question|flow|columns)\s*\n(?P<body>.*?)\n:::",
    re.DOTALL | re.IGNORECASE,
)
KEY_MESSAGE_RE = re.compile(
    r"^\s*\*\*Key Message:\*\*\s*(?P<body>.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


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


def _md(text: str) -> str:
    return md.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "smarty"],
        output_format="html5",
    )


def _render_question(body: str) -> str:
    inner = _md(body.strip())
    return (
        '<aside class="question">'
        '<span class="label">Question</span>'
        f"{inner}"
        "</aside>"
    )


def _render_flow(body: str) -> str:
    # Prefer arrow chains on a single line: A -> B -> C
    # Also accept one node per line.
    nodes: list[str] = []
    for line in body.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if "->" in line:
            nodes.extend(part.strip() for part in line.split("->") if part.strip())
        else:
            nodes.append(line)
    if not nodes:
        return '<div class="flow"></div>'
    parts = ['<div class="flow">']
    for node in nodes:
        parts.append(f'<div class="flow-node">{html.escape(node)}</div>')
    parts.append("</div>")
    return "\n".join(parts)


def _render_columns(body: str) -> str:
    cols = [c.strip() for c in re.split(r"\n\+\+\+\n", body.strip())]
    parts = ['<div class="columns">']
    for col in cols:
        parts.append(f'<div class="column">{_md(col)}</div>')
    parts.append("</div>")
    return "\n".join(parts)


def _inline_md(text: str) -> str:
    """Render a single-line fragment to HTML without wrapping <p>."""
    rendered = _md(text).strip()
    if rendered.startswith("<p>") and rendered.endswith("</p>"):
        rendered = rendered[3:-4]
    return rendered


def _render_key_messages(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        body = match.group("body").strip()
        return (
            '<div class="key-message">'
            '<span class="label">Key Message: </span>'
            f"{_inline_md(body)}"
            "</div>"
        )

    return KEY_MESSAGE_RE.sub(repl, text)


_RENDERERS = {
    "question": _render_question,
    "flow": _render_flow,
    "columns": _render_columns,
}


def render_slide_markdown(slide_md: str) -> str:
    text = _render_key_messages(slide_md)
    chunks: list[str] = []
    pos = 0
    for match in FENCE_BLOCK_RE.finditer(text):
        before = text[pos : match.start()]
        if before.strip():
            chunks.append(_md(before))
        kind = match.group("kind").lower()
        chunks.append(_RENDERERS[kind](match.group("body")))
        pos = match.end()
    after = text[pos:]
    if after.strip():
        chunks.append(_md(after))
    return "\n".join(chunks)


def parse_deck(text: str) -> tuple[dict[str, Any], list[str]]:
    meta, body = split_front_matter(text)
    slides = [render_slide_markdown(s) for s in split_slides(body)]
    if not slides:
        raise ValueError("No slides found. Separate slides with a --- line.")
    return meta, slides
