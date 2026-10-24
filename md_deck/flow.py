"""Parse ::: flow bodies into lanes, nodes, chain edges, and cross-lane links."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

KNOWN_NODE_KINDS = frozenset({"actor", "system", "doc", "muted", "highlight"})

# Longest operators first.
ARROW_RE = re.compile(
    r"(?P<op>"
    r"<\-\[[^\]]*\]\->"
    r"|-\[[^\]]*\]\->"
    r"|-\.\[[^\]]*\]\.\->"
    r"|<\->"
    r"|\.\.>"
    r"|\->"
    r")"
)

LANE_RE = re.compile(r"^lane:\s*(?P<label>.*)$", re.IGNORECASE)
LINK_RE = re.compile(
    r"^link:\s*(?P<src>.+?)\s*"
    r"(?P<style>=>|\.\.>|\->)"
    r"\s*(?P<dst>.+?)"
    r"(?:\s*:\s*(?P<label>.*))?$",
    re.IGNORECASE,
)

KIND_RE = re.compile(
    r"^\[(?P<kind>actor|system|doc|muted|highlight)\]\s*(?P<rest>.+)$",
    re.IGNORECASE,
)
BADGE_RE = re.compile(r"^(?P<head>.*?)\s*\{(?P<badge>[^{}]+)\}\s*$")


@dataclass
class FlowNode:
    key: str
    title: str
    kind: str | None = None
    caption: str | None = None
    badge: str | None = None


@dataclass
class FlowEdge:
    source: str
    target: str
    style: str = "solid"  # solid | dashed
    label: str | None = None
    bidirectional: bool = False


@dataclass
class FlowLane:
    label: str | None = None
    node_keys: list[str] = field(default_factory=list)
    edges: list[FlowEdge] = field(default_factory=list)


@dataclass
class FlowDiagram:
    lanes: list[FlowLane] = field(default_factory=list)
    nodes: dict[str, FlowNode] = field(default_factory=dict)
    links: list[FlowEdge] = field(default_factory=list)
    options: frozenset[str] = field(default_factory=frozenset)
    errors: list[str] = field(default_factory=list)


def _hard_breaks(text: str) -> str:
    """Turn trailing backslash line-breaks into <br> markers inside node text."""
    return text.replace("\\n", "\n").replace("\\\n", "\n")


def parse_node_text(raw: str) -> FlowNode:
    text = raw.strip()
    kind: str | None = None
    match = KIND_RE.match(text)
    if match:
        kind = match.group("kind").lower()
        text = match.group("rest").strip()

    badge: str | None = None
    badge_match = BADGE_RE.match(text)
    if badge_match:
        text = badge_match.group("head").strip()
        badge = badge_match.group("badge").strip() or None

    caption: str | None = None
    if " | " in text:
        title, caption = text.split(" | ", 1)
        title = title.strip()
        caption = caption.strip() or None
    elif text.endswith("|"):
        title = text[:-1].strip()
        caption = None
    else:
        # Allow Name|caption without spaces when unambiguous
        if "|" in text and "{" not in text:
            title, _, rest = text.partition("|")
            title = title.strip()
            caption = rest.strip() or None
        else:
            title = text

    title = _hard_breaks(title)
    if caption:
        caption = _hard_breaks(caption)
    if not title:
        title = raw.strip() or "?"
    return FlowNode(key=title, title=title, kind=kind, caption=caption, badge=badge)


def _parse_arrow(op: str) -> tuple[str, str | None, bool]:
    """Return (style, label, bidirectional)."""
    if op == "<->":
        return "solid", None, True
    if op == "..>":
        return "dashed", None, False
    if op == "->":
        return "solid", None, False
    if op.startswith("<-[") and op.endswith("]->"):
        return "solid", op[3:-3], True
    if op.startswith("-.[") and op.endswith("].->"):
        return "dashed", op[3:-4], False
    if op.startswith("-[") and op.endswith("]->"):
        return "solid", op[2:-3], False
    return "solid", None, False


def _allocate_key(diagram: FlowDiagram, title: str) -> str:
    """Unique data-node key; duplicate titles get a #N suffix (display title unchanged)."""
    if title not in diagram.nodes:
        return title
    n = 2
    while f"{title}#{n}" in diagram.nodes:
        n += 1
    return f"{title}#{n}"


def _find_key_by_title(diagram: FlowDiagram, title: str) -> str | None:
    """Resolve a link endpoint title to the most recently defined matching node."""
    matches = [
        key
        for key, node in diagram.nodes.items()
        if node.title == title or key == title
    ]
    return matches[-1] if matches else None


def _ensure_node(diagram: FlowDiagram, raw: str, *, reuse: bool = False) -> str:
    node = parse_node_text(raw)
    if not node.title.strip():
        diagram.errors.append("empty flow node in arrow chain")
        return ""
    if reuse:
        found = _find_key_by_title(diagram, node.title)
        if found is not None:
            existing = diagram.nodes[found]
            if existing.kind is None and node.kind is not None:
                existing.kind = node.kind
            if existing.caption is None and node.caption is not None:
                existing.caption = node.caption
            if existing.badge is None and node.badge is not None:
                existing.badge = node.badge
            return found
    key = _allocate_key(diagram, node.title)
    node.key = key
    diagram.nodes[key] = node
    return key


def _parse_chain_line(diagram: FlowDiagram, lane: FlowLane, line: str) -> None:
    parts: list[str] = []
    ops: list[str] = []
    pos = 0
    for match in ARROW_RE.finditer(line):
        left = line[pos : match.start()].strip()
        parts.append(left)
        ops.append(match.group("op"))
        pos = match.end()
    tail = line[pos:].strip()
    parts.append(tail)

    if len(parts) == 1 and not ops:
        # Lone node on a line (still allowed; may accumulate)
        key = _ensure_node(diagram, parts[0])
        if key and key not in lane.node_keys:
            lane.node_keys.append(key)
        return

    if any(not p for p in parts):
        diagram.errors.append("empty flow node in arrow chain")

    keys: list[str] = []
    for part in parts:
        if not part:
            keys.append("")
            continue
        keys.append(_ensure_node(diagram, part))

    for key in keys:
        if key and key not in lane.node_keys:
            lane.node_keys.append(key)

    for i, op in enumerate(ops):
        src, dst = keys[i], keys[i + 1]
        if not src or not dst:
            continue
        style, label, bidirectional = _parse_arrow(op)
        lane.edges.append(
            FlowEdge(
                source=src,
                target=dst,
                style=style,
                label=label,
                bidirectional=bidirectional,
            )
        )


def _parse_link_line(diagram: FlowDiagram, line: str) -> None:
    match = LINK_RE.match(line.strip())
    if not match:
        diagram.errors.append(f"malformed link line: {line.strip()!r}")
        return
    src_raw = match.group("src").strip()
    dst_raw = match.group("dst").strip()
    style_tok = match.group("style")
    label = (match.group("label") or "").strip() or None
    # Links refer to existing nodes by title; create only if missing.
    src = _ensure_node(diagram, src_raw, reuse=True)
    dst = _ensure_node(diagram, dst_raw, reuse=True)
    if not src or not dst:
        return
    style = "dashed" if style_tok == "..>" else "solid"
    diagram.links.append(
        FlowEdge(source=src, target=dst, style=style, label=label)
    )


def parse_flow_body(body: str, options: frozenset[str] | None = None) -> FlowDiagram:
    diagram = FlowDiagram(options=options or frozenset())
    current: FlowLane | None = None

    def ensure_lane() -> FlowLane:
        nonlocal current
        if current is None:
            current = FlowLane()
            diagram.lanes.append(current)
        return current

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lane_match = LANE_RE.match(line)
        if lane_match:
            current = FlowLane(label=lane_match.group("label").strip() or None)
            diagram.lanes.append(current)
            continue
        if LINK_RE.match(line):
            _parse_link_line(diagram, line)
            continue
        _parse_chain_line(diagram, ensure_lane(), line)

    # Backward compatible: nodes listed one per line (no arrows) still chain left→right.
    for lane in diagram.lanes:
        if len(lane.node_keys) >= 2 and not lane.edges:
            for i in range(len(lane.node_keys) - 1):
                lane.edges.append(
                    FlowEdge(
                        source=lane.node_keys[i],
                        target=lane.node_keys[i + 1],
                        style="solid",
                    )
                )

    return diagram


def _node_inner_html(node: FlowNode) -> str:
    title = html.escape(node.title).replace("\n", "<br/>")
    parts = [f'<span class="flow-node-title">{title}</span>']
    if node.caption:
        cap = html.escape(node.caption).replace("\n", "<br/>")
        parts.append(f'<span class="flow-node-caption">{cap}</span>')
    if node.badge:
        parts.append(
            f'<span class="flow-node-badge">{html.escape(node.badge)}</span>'
        )
    return "".join(parts)


def render_flow_html(diagram: FlowDiagram) -> str:
    option_classes = " ".join(sorted(f"flow-{opt}" for opt in diagram.options))
    class_attr = "flow" + (f" {option_classes}" if option_classes else "")
    parts = [f'<div class="{class_attr}">']

    if len(diagram.lanes) > 1 or any(lane.label for lane in diagram.lanes):
        parts.append('<div class="flow-lanes">')
        for index, lane in enumerate(diagram.lanes):
            parts.append(f'<div class="lane" data-lane="{index}">')
            if lane.label:
                parts.append(
                    f'<div class="lane-label">{html.escape(lane.label)}</div>'
                )
            parts.append('<div class="flow-row">')
            for key in lane.node_keys:
                node = diagram.nodes[key]
                parts.append(_render_node(node))
            parts.append("</div>")  # flow-row
            for edge in lane.edges:
                parts.append(_render_edge(edge, cross=False))
            parts.append("</div>")  # lane
        parts.append("</div>")  # flow-lanes
    else:
        # Single lane, flat layout (backward compatible DOM)
        lane = diagram.lanes[0] if diagram.lanes else FlowLane()
        for key in lane.node_keys:
            parts.append(_render_node(diagram.nodes[key]))
        for edge in lane.edges:
            parts.append(_render_edge(edge, cross=False))

    for edge in diagram.links:
        parts.append(_render_edge(edge, cross=True))

    parts.append("</div>")
    return "\n".join(parts)


def _render_node(node: FlowNode) -> str:
    kind_attr = f' data-kind="{html.escape(node.kind)}"' if node.kind else ""
    kind_class = f" flow-node-{node.kind}" if node.kind else ""
    return (
        f'<div class="flow-node{kind_class}" data-node="{html.escape(node.key)}"'
        f"{kind_attr}>{_node_inner_html(node)}</div>"
    )


def _render_edge(edge: FlowEdge, *, cross: bool) -> str:
    classes = "flow-edge"
    if cross:
        classes += " flow-edge-cross"
    label_attr = (
        f' data-label="{html.escape(edge.label)}"' if edge.label is not None else ""
    )
    bi = ' data-bidirectional="true"' if edge.bidirectional else ""
    return (
        f'<div class="{classes}" data-from="{html.escape(edge.source)}" '
        f'data-to="{html.escape(edge.target)}" data-style="{edge.style}"'
        f"{label_attr}{bi}></div>"
    )


def collect_flow_nodes(body: str) -> tuple[list[str], list[str]]:
    """Validation helper: return (node_keys_in_order, error messages)."""
    diagram = parse_flow_body(body)
    keys: list[str] = []
    for lane in diagram.lanes:
        for key in lane.node_keys:
            if key not in keys:
                keys.append(key)
    for edge in diagram.links:
        for key in (edge.source, edge.target):
            if key not in keys:
                keys.append(key)
    return keys, list(diagram.errors)
