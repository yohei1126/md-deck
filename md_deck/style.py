"""Parse deck style Markdown into CSS variables and optional extra rules."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# Token name -> (css variable, default used only when building docs examples).
# The generator does not apply a built-in visual theme; these defaults are the
# plain fallback values when a listed token is omitted from a style file.
TOKEN_SPEC: dict[str, tuple[str, Any]] = {
    "page_width": ("--page-width", "1280px"),
    "page_height": ("--page-height", "720px"),
    "color_background": ("--color-background", "#ffffff"),
    "color_text": ("--color-text", "#000000"),
    "color_muted": ("--color-muted", "#444444"),
    "color_gray": ("--color-gray", "#444444"),
    "color_border": ("--color-border", "#cccccc"),
    "color_title": ("--color-title", "#000000"),
    "color_top_bar": ("--color-top-bar", "#000000"),
    "color_accent_2": ("--color-accent-2", "#666666"),
    "color_highlight": ("--color-highlight", "#000000"),
    "color_highlight_bg": ("--color-highlight-bg", "#f5f5f5"),
    "color_key_message_bg": ("--color-key-message-bg", "#f5f5f5"),
    "color_key_message_text": ("--color-key-message-text", "#000000"),
    "color_key_message_border": ("--color-key-message-border", "#cccccc"),
    "color_question_bg": ("--color-question-bg", "#f5f5f5"),
    "color_question_text": ("--color-question-text", "#000000"),
    "color_question_border": ("--color-question-border", "#cccccc"),
    "color_card_bg": ("--color-card-bg", "#ffffff"),
    "color_card_border": ("--color-card-border", "#cccccc"),
    "color_flow_node_bg": ("--color-flow-node-bg", "#ffffff"),
    "color_flow_node_border": ("--color-flow-node-border", "#000000"),
    "color_flow_arrow": ("--color-flow-arrow", "#000000"),
    "color_table_header_bg": ("--color-table-header-bg", "#f0f0f0"),
    "color_table_border": ("--color-table-border", "#cccccc"),
    "font_family": ("--font-family", "sans-serif"),
    "font_size_body": ("--font-size-body", "22px"),
    "font_size_title": ("--font-size-title", "36px"),
    "font_size_key_message": ("--font-size-key-message", "20px"),
    "font_size_question": ("--font-size-question", "18px"),
    "font_size_small": ("--font-size-small", "16px"),
    "font_size_table": ("--font-size-table", "16px"),
    "font_weight_title": ("--font-weight-title", "700"),
    "font_weight_body": ("--font-weight-body", "400"),
    "source_label_weight": ("--source-label-weight", "600"),
    "source_label_gap": ("--source-label-gap", "0.15em"),
    "line_height": ("--line-height", "1.45"),
    "page_padding": ("--page-padding", "48px"),
    "page_padding_top": ("--page-padding-top", "48px"),
    "page_padding_right": ("--page-padding-right", "48px"),
    "page_padding_bottom": ("--page-padding-bottom", "48px"),
    "page_padding_left": ("--page-padding-left", "48px"),
    "footer_inset_bottom": ("--footer-inset-bottom", "0.6em"),
    "footer_inset_right": ("--footer-inset-right", "0px"),
    "gap": ("--gap", "16px"),
    "flow_callout_gap": ("--flow-callout-gap", "12px"),
    "flow_port_gap": ("--flow-port-gap", "12px"),
    "flow_edge_shape": ("--flow-edge-shape", "orthogonal"),
    "card_radius": ("--card-radius", "8px"),
    "card_padding": ("--card-padding", "16px"),
    "key_message_radius": ("--key-message-radius", "8px"),
    "question_radius": ("--question-radius", "8px"),
    "border_width": ("--border-width", "1px"),
    "flow_node_min_width": ("--flow-node-min-width", "120px"),
    "flow_node_max_width": ("--flow-node-max-width", "none"),
    "flow_node_min_height": ("--flow-node-min-height", "96px"),
    "flow_stack_gap": ("--flow-stack-gap", "32px"),
    # CSS flex-grow: 0 keeps boxes content-sized; 1 stretches them to leftover height.
    "flow_fill_height": ("--flow-fill-height", "0"),
    # Wide rows with no stack grow toward this share of the slide content box.
    # none keeps content height. flow_fill_height: fill removes the cap.
    "flow_preferred_height": ("--flow-preferred-height", "60%"),
    "column_min_height": ("--column-min-height", "160px"),
    "flow_node_padding": ("--flow-node-padding", "12px"),
    "label_question": ("--label-question", "Question"),
    "label_key_message": ("--label-key-message", "Key Message"),
    "label_source": ("--label-source", "Source:"),
    "question_label_placement": ("--question-label-placement", "inline"),
    "page_number_placement": ("--page-number-placement", "bottom-right"),
}

# Tokens that may be 0 or the keyword none (radii, borders, paddings).
ZERO_OR_NONE_TOKENS = frozenset(
    {
        "card_radius",
        "key_message_radius",
        "question_radius",
        "border_width",
        "page_padding",
        "page_padding_top",
        "page_padding_right",
        "page_padding_bottom",
        "page_padding_left",
        "footer_inset_bottom",
        "footer_inset_right",
        "card_padding",
        "gap",
        "flow_callout_gap",
        "flow_port_gap",
        "flow_node_padding",
        "flow_node_min_width",
        "flow_node_max_width",
        "flow_node_min_height",
        "flow_preferred_height",
        "flow_stack_gap",
        "column_min_height",
        "source_label_gap",
    }
)

# Footer insets may be negative (pull toward the page edge past page padding).
SIGNED_SIZE_TOKENS = frozenset({"footer_inset_bottom", "footer_inset_right"})

LABEL_TOKENS = frozenset({"label_question", "label_key_message", "label_source"})
# label_source may be "" to hide the footer prefix; other labels stay non-empty.
OPTIONAL_EMPTY_LABEL_TOKENS = frozenset({"label_source"})
PLACEMENT_TOKENS = frozenset({"question_label_placement", "page_number_placement"})
PAGE_NUMBER_PLACEMENTS = frozenset(
    {"bottom-right", "bottom-left", "bottom-center"}
)
QUESTION_LABEL_PLACEMENTS = frozenset({"inline", "block"})
EDGE_SHAPE_TOKENS = frozenset({"flow_edge_shape"})
EDGE_SHAPES = frozenset({"orthogonal", "straight"})
FILL_HEIGHT_TOKENS = frozenset({"flow_fill_height"})
FILL_HEIGHT_ON = frozenset({"fill", "1", "true", "yes"})
FILL_HEIGHT_VALUES = frozenset({"none", "fill"})

FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
CSS_FENCE_RE = re.compile(r"```css\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def _format_css_value(token: str, value: Any) -> str:
    if value is None:
        return str(TOKEN_SPEC[token][1])
    if isinstance(value, bool):
        return "true" if value else "false"
    if token in LABEL_TOKENS:
        # CSS string for content: var(--label-question)
        text = str(value).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{text}"'
    if token in PLACEMENT_TOKENS or token in EDGE_SHAPE_TOKENS:
        return str(value).strip().lower()
    if token in FILL_HEIGHT_TOKENS:
        text = str(value).strip().lower()
        return "1" if text in FILL_HEIGHT_ON else "0"
    if isinstance(value, str) and value.strip().lower() == "none":
        return "none"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # Bare numbers for sizes become px, except unitless line-height / weights.
        if token in {
            "line_height",
            "font_weight_title",
            "font_weight_body",
            "source_label_weight",
        }:
            return str(value)
        return f"{value}px"
    text = str(value).strip()
    return text


def parse_style_markdown(text: str) -> tuple[dict[str, Any], str]:
    """Return (tokens, extra_css). Prose outside front matter / css fences is ignored."""
    tokens: dict[str, Any] = {}
    rest = text
    match = FRONT_MATTER_RE.match(text)
    if match:
        loaded = yaml.safe_load(match.group(1)) or {}
        if not isinstance(loaded, dict):
            raise ValueError("Style front matter must be a YAML mapping of tokens.")
        tokens = loaded
        rest = text[match.end() :]

    extras = [block.strip() for block in CSS_FENCE_RE.findall(rest) if block.strip()]
    return tokens, "\n\n".join(extras)


def load_style_file(path: Path) -> tuple[dict[str, Any], str]:
    return parse_style_markdown(path.read_text(encoding="utf-8"))


def _expand_padding_sides(tokens: dict[str, Any]) -> dict[str, Any]:
    """Fill per-side page padding from page_padding when a side is omitted."""
    out = dict(tokens)
    base = out.get("page_padding")
    if base is None:
        return out
    for side in ("top", "right", "bottom", "left"):
        key = f"page_padding_{side}"
        if key not in out:
            out[key] = base
    return out


def _preferred_height_vars(tokens: dict[str, Any]) -> tuple[str, str]:
    """Return (--flow-preferred-height, --flow-preferred-grow).

    A wide row with no stack grows toward the height. ``none`` / ``0`` keeps the
    content height. ``flow_fill_height: fill`` removes the cap.
    """
    fill_raw = tokens.get("flow_fill_height")
    if fill_raw is not None and str(fill_raw).strip().lower() in FILL_HEIGHT_ON:
        return "none", "1"
    raw = tokens.get("flow_preferred_height")
    if raw is None:
        return "60%", "1"
    if isinstance(raw, str) and raw.strip().lower() in {"none", "0", "0px", "0%", "0em", "0rem"}:
        return "none", "0"
    if isinstance(raw, (int, float)) and not isinstance(raw, bool) and float(raw) == 0:
        return "none", "0"
    return _format_css_value("flow_node_min_height", raw), "1"


def tokens_to_css(tokens: dict[str, Any], extra_css: str = "") -> str:
    """Build a :root rule from tokens, filling omitted tokens with plain defaults."""
    unknown = sorted(set(tokens) - set(TOKEN_SPEC))
    if unknown:
        raise ValueError(
            "Unknown style token(s): "
            + ", ".join(unknown)
            + ". See docs/STYLE_GUIDE.md for the schema."
        )

    expanded = _expand_padding_sides(tokens)
    preferred_height, preferred_grow = _preferred_height_vars(expanded)
    # font_size_table falls back to font_size_small when omitted.
    if "font_size_table" not in expanded and "font_size_small" in expanded:
        expanded["font_size_table"] = expanded["font_size_small"]

    lines = [":root {"]
    for name, (css_var, default) in TOKEN_SPEC.items():
        raw = expanded[name] if name in expanded else default
        if name == "flow_preferred_height":
            lines.append(f"  {css_var}: {preferred_height};")
            lines.append(f"  --flow-preferred-grow: {preferred_grow};")
            continue
        if name in expanded:
            value = _format_css_value(name, raw)
        else:
            value = str(default)
            if name in LABEL_TOKENS and not str(default).startswith('"'):
                value = f'"{default}"'
        lines.append(f"  {css_var}: {value};")
    lines.append("}")
    parts = ["\n".join(lines)]
    if extra_css.strip():
        parts.append(extra_css.strip())
    return "\n\n".join(parts) + "\n"


def resolve_style_path(
    cli_style: Path | None,
    source_meta: dict[str, Any],
    source_path: Path,
) -> Path:
    """Require a style file from --style or the slides' `style:` front matter."""
    if cli_style is not None:
        path = cli_style
    else:
        rel = source_meta.get("style")
        if not rel:
            raise SystemExit(
                "No style file given. Pass --style path/to/deck_style.md "
                "or set `style: deck_style.md` in the slides front matter. "
                "md-deck has no built-in visual theme; each deck repo supplies style."
            )
        path = Path(str(rel))
        if not path.is_absolute():
            path = (source_path.parent / path).resolve()

    if not path.is_file():
        raise SystemExit(f"Style file not found: {path}")
    return path.resolve()
