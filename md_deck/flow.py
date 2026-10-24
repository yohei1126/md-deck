"""Parse ::: flow bodies into lanes, nodes, chain edges, and cross-lane links."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

KNOWN_NODE_KINDS = frozenset({"actor", "system", "doc", "muted", "highlight"})
KNOWN_LINK_ROUTES = frozenset({"up", "down", "left", "right", "auto"})
KNOWN_CALLOUT_POS = frozenset({"above", "below", "left", "right"})

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
    r"(?:\s*:\s*(?P<label>.*?))?"
    r"(?:\s*\[(?P<opts>[^\]]*)\])?\s*$",
    re.IGNORECASE,
)
CALLOUT_RE = re.compile(
    r"^callout:\s*(?P<anchor>.+?)\s*:\s*(?P<text>.*?)"
    r"(?:\s*\[(?P<opts>[^\]]*)\])?\s*$",
    re.IGNORECASE,
)
KIND_RE = re.compile(
    r"^\[(?P<kind>actor|system|doc|muted|highlight)\]\s*(?P<rest>.+)$",
    re.IGNORECASE,
)
# Explicit node id: {#id} (must start with #)
NODE_ID_RE = re.compile(r"\{#(?P<id>[A-Za-z][\w-]*)\}")
# Badge: {text} that is not {#id}
BADGE_RE = re.compile(r"\{(?![#])(?P<badge>[^{}]+)\}")
# Stack group in a chain: { A / B / C } or { A; B }
STACK_OPEN_RE = re.compile(r"^\{\s*(?P<body>.*?)\s*\}\s*$", re.DOTALL)


@dataclass
class FlowNode:
    key: str
    title: str
    kind: str | None = None
    caption: str | None = None
    badge: str | None = None
    node_id: str | None = None
    chips: list[str] = field(default_factory=list)


@dataclass
class FlowEdge:
    source: str
    target: str
    style: str = "solid"  # solid | dashed
    label: str | None = None
    bidirectional: bool = False
    cross: bool = False
    route: str = "auto"  # up | down | left | right | auto
    pair_index: int = 0
    pair_count: int = 1


@dataclass
class FlowCallout:
    anchor: str
    text: str
    pos: str = "below"  # above | below | left | right


@dataclass
class FlowLane:
    label: str | None = None
    # Each entry is either a node key (str) or a stack (list[str] of keys).
    columns: list[str | list[str]] = field(default_factory=list)
    edges: list[FlowEdge] = field(default_factory=list)

    @property
    def node_keys(self) -> list[str]:
        keys: list[str] = []
        for col in self.columns:
            if isinstance(col, list):
                keys.extend(col)
            else:
                keys.append(col)
        return keys


@dataclass
class FlowDiagram:
    lanes: list[FlowLane] = field(default_factory=list)
    nodes: dict[str, FlowNode] = field(default_factory=dict)
    links: list[FlowEdge] = field(default_factory=list)
    callouts: list[FlowCallout] = field(default_factory=list)
    options: frozenset[str] = field(default_factory=frozenset)
    errors: list[str] = field(default_factory=list)


def _hard_breaks(text: str) -> str:
    """Turn \\n / trailing-backslash breaks into real newlines."""
    text = text.replace("\\n", "\n")
    text = text.replace("\\\n", "\n")
    return text


def _parse_opts_map(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    out: dict[str, str] = {}
    for part in re.split(r"[,\s]+", raw.strip()):
        if not part or "=" not in part:
            continue
        key, _, val = part.partition("=")
        out[key.strip().lower()] = val.strip().lower()
    return out


def parse_node_text(raw: str) -> FlowNode:
    text = raw.strip()
    kind: str | None = None
    match = KIND_RE.match(text)
    if match:
        kind = match.group("kind").lower()
        text = match.group("rest").strip()

    chips: list[str] = []
    chips_match = re.search(r"\[\[(?P<chips>[^\]]*)\]\]", text)
    if chips_match:
        chips_raw = chips_match.group("chips")
        chips = [c.strip() for c in re.split(r"[,;/]", chips_raw) if c.strip()]
        chips = [_hard_breaks(c) for c in chips]
        text = (text[: chips_match.start()] + text[chips_match.end() :]).strip()

    node_id: str | None = None
    id_match = NODE_ID_RE.search(text)
    if id_match:
        node_id = id_match.group("id")
        text = (text[: id_match.start()] + text[id_match.end() :]).strip()

    badge: str | None = None
    badge_match = BADGE_RE.search(text)
    if badge_match:
        badge = _hard_breaks(badge_match.group("badge").strip()) or None
        text = (text[: badge_match.start()] + text[badge_match.end() :]).strip()

    caption: str | None = None
    if " | " in text:
        title, caption = text.split(" | ", 1)
        title = title.strip()
        caption = caption.strip() or None
    elif text.endswith("|"):
        title = text[:-1].strip()
        caption = None
    else:
        if "|" in text and "{" not in text and "[[" not in text:
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
    key = node_id or title
    return FlowNode(
        key=key,
        title=title,
        kind=kind,
        caption=caption,
        badge=badge,
        node_id=node_id,
        chips=chips,
    )


def _parse_arrow(op: str) -> tuple[str, str | None, bool]:
    """Return (style, label, bidirectional)."""
    if op == "<->":
        return "solid", None, True
    if op == "..>":
        return "dashed", None, False
    if op == "->":
        return "solid", None, False
    if op.startswith("<-[") and op.endswith("]->"):
        return "solid", _hard_breaks(op[3:-3]), True
    if op.startswith("-.[") and op.endswith("].->"):
        return "dashed", _hard_breaks(op[3:-4]), False
    if op.startswith("-[") and op.endswith("]->"):
        return "solid", _hard_breaks(op[2:-3]), False
    return "solid", None, False


def _allocate_key(diagram: FlowDiagram, preferred: str) -> str:
    """Unique data-node key; duplicate preferred keys get a #N suffix."""
    if preferred not in diagram.nodes:
        return preferred
    n = 2
    while f"{preferred}#{n}" in diagram.nodes:
        n += 1
    return f"{preferred}#{n}"


def _find_key(diagram: FlowDiagram, ref: str) -> str | None:
    """Resolve a link/callout endpoint by id, key, or title (most recent match)."""
    ref = ref.strip()
    if ref in diagram.nodes:
        return ref
    matches = [
        key
        for key, node in diagram.nodes.items()
        if node.node_id == ref or node.title == ref or key == ref
    ]
    return matches[-1] if matches else None


def _merge_node_fields(existing: FlowNode, node: FlowNode) -> None:
    if existing.kind is None and node.kind is not None:
        existing.kind = node.kind
    if existing.caption is None and node.caption is not None:
        existing.caption = node.caption
    if existing.badge is None and node.badge is not None:
        existing.badge = node.badge
    if not existing.chips and node.chips:
        existing.chips = list(node.chips)


def _ensure_node(
    diagram: FlowDiagram,
    raw: str,
    *,
    reuse: bool = False,
    lane: FlowLane | None = None,
) -> str:
    node = parse_node_text(raw)
    if not node.title.strip() and not node.node_id:
        diagram.errors.append("empty flow node in arrow chain")
        return ""
    if reuse:
        found = _find_key(diagram, node.node_id or node.title)
        if found is not None:
            _merge_node_fields(diagram.nodes[found], node)
            return found
    # Re-mentions inside the same lane reuse the existing node (parallel edges).
    if lane is not None:
        for key in lane.node_keys:
            existing = diagram.nodes[key]
            if node.node_id and existing.node_id == node.node_id:
                _merge_node_fields(existing, node)
                return key
            if not node.node_id and existing.title == node.title:
                _merge_node_fields(existing, node)
                return key
    preferred = node.node_id or node.title
    if node.node_id and node.node_id in diagram.nodes:
        diagram.errors.append(f"duplicate flow node id {node.node_id!r}")
        key = _allocate_key(diagram, preferred)
    else:
        key = _allocate_key(diagram, preferred)
    node.key = key
    diagram.nodes[key] = node
    return key


def _is_stack_literal(raw: str) -> bool:
    """True for `{ A / B }` stacks; false for badge-only `{badge}`."""
    match = STACK_OPEN_RE.match(raw.strip())
    if not match:
        return False
    body = match.group("body")
    return bool(re.search(r"[/\n;]", body))


def _parse_stack_body(diagram: FlowDiagram, body: str) -> list[str]:
    """Parse stacked node names separated by / or newlines."""
    parts = re.split(r"[/\n;]+", body.strip())
    keys: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        key = _ensure_node(diagram, part)
        if key:
            keys.append(key)
    if len(keys) < 2:
        diagram.errors.append(
            "stacked nodes need at least two names inside { A / B }"
        )
    return keys


def _split_chain_parts(line: str) -> tuple[list[str], list[str]]:
    """Split a chain line into node/stack parts and operators, honouring { stacks }."""
    depths = [0] * (len(line) + 1)
    depth = 0
    for i, ch in enumerate(line):
        depths[i] = depth
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
    depths[len(line)] = depth

    parts: list[str] = []
    ops: list[str] = []
    pos = 0
    for match in ARROW_RE.finditer(line):
        if depths[match.start()] > 0:
            continue
        parts.append(line[pos : match.start()].strip())
        ops.append(match.group("op"))
        pos = match.end()
    parts.append(line[pos:].strip())
    return parts, ops


def _add_column(lane: FlowLane, key_or_stack: str | list[str]) -> None:
    if isinstance(key_or_stack, list):
        for key in key_or_stack:
            # Avoid duplicating keys already present as lone columns
            pass
        lane.columns.append(key_or_stack)
        return
    # Dedup lone keys
    for col in lane.columns:
        if col == key_or_stack:
            return
        if isinstance(col, list) and key_or_stack in col:
            return
    lane.columns.append(key_or_stack)


def _parse_chain_line(diagram: FlowDiagram, lane: FlowLane, line: str) -> None:
    parts, ops = _split_chain_parts(line)

    if len(parts) == 1 and not ops:
        raw = parts[0]
        if _is_stack_literal(raw):
            keys = _parse_stack_body(diagram, STACK_OPEN_RE.match(raw).group("body"))  # type: ignore[union-attr]
            if keys:
                _add_column(lane, keys)
            return
        key = _ensure_node(diagram, raw, lane=lane)
        if key:
            _add_column(lane, key)
        return

    if any(not p for p in parts):
        diagram.errors.append("empty flow node in arrow chain")

    resolved: list[str | list[str] | None] = []
    for part in parts:
        if not part:
            resolved.append(None)
            continue
        if _is_stack_literal(part):
            keys = _parse_stack_body(
                diagram, STACK_OPEN_RE.match(part).group("body")  # type: ignore[union-attr]
            )
            resolved.append(keys if keys else None)
            continue
        key = _ensure_node(diagram, part, lane=lane)
        resolved.append(key or None)

    for item in resolved:
        if item is None:
            continue
        _add_column(lane, item)

    for i, op in enumerate(ops):
        src_item, dst_item = resolved[i], resolved[i + 1]
        if src_item is None or dst_item is None:
            continue
        # Edges from/to stacks connect the first node of each stack column.
        src = src_item[0] if isinstance(src_item, list) else src_item
        dst = dst_item[0] if isinstance(dst_item, list) else dst_item
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
    label_raw = match.group("label")
    label = _hard_breaks(label_raw.strip()) if label_raw and label_raw.strip() else None
    opts = _parse_opts_map(match.group("opts"))
    route = opts.get("route", "auto")
    if route not in KNOWN_LINK_ROUTES:
        diagram.errors.append(
            f"unknown link route {route!r} "
            f"(expected {', '.join(sorted(KNOWN_LINK_ROUTES))})"
        )
        route = "auto"
    src = _ensure_node(diagram, src_raw, reuse=True)
    dst = _ensure_node(diagram, dst_raw, reuse=True)
    if not src or not dst:
        return
    style = "dashed" if style_tok == "..>" else "solid"
    diagram.links.append(
        FlowEdge(
            source=src,
            target=dst,
            style=style,
            label=label,
            cross=True,
            route=route,
        )
    )


def _parse_callout_line(diagram: FlowDiagram, line: str) -> None:
    match = CALLOUT_RE.match(line.strip())
    if not match:
        diagram.errors.append(f"malformed callout line: {line.strip()!r}")
        return
    anchor_raw = match.group("anchor").strip()
    text = _hard_breaks(match.group("text").strip())
    if not text:
        diagram.errors.append("callout text is empty")
        return
    opts = _parse_opts_map(match.group("opts"))
    pos = opts.get("pos", "below")
    if pos not in KNOWN_CALLOUT_POS:
        diagram.errors.append(
            f"unknown callout pos {pos!r} "
            f"(expected {', '.join(sorted(KNOWN_CALLOUT_POS))})"
        )
        pos = "below"
    anchor = _ensure_node(diagram, anchor_raw, reuse=True)
    if not anchor:
        return
    diagram.callouts.append(FlowCallout(anchor=anchor, text=text, pos=pos))


def _assign_parallel_indices(edges: list[FlowEdge]) -> None:
    """Offset parallel edges between the same unordered pair."""
    groups: dict[tuple[str, str], list[FlowEdge]] = {}
    for edge in edges:
        key = tuple(sorted((edge.source, edge.target)))
        groups.setdefault(key, []).append(edge)
    for group in groups.values():
        n = len(group)
        for i, edge in enumerate(group):
            edge.pair_index = i
            edge.pair_count = n


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
        if CALLOUT_RE.match(line):
            _parse_callout_line(diagram, line)
            continue
        _parse_chain_line(diagram, ensure_lane(), line)

    # Backward compatible: nodes listed one per line (no arrows) still chain left→right.
    for lane in diagram.lanes:
        if len(lane.columns) >= 2 and not lane.edges:
            keys = []
            for col in lane.columns:
                keys.append(col[0] if isinstance(col, list) else col)
            for i in range(len(keys) - 1):
                lane.edges.append(
                    FlowEdge(
                        source=keys[i],
                        target=keys[i + 1],
                        style="solid",
                    )
                )

    all_edges = [e for lane in diagram.lanes for e in lane.edges] + list(diagram.links)
    _assign_parallel_indices(all_edges)
    return diagram


def _br_escape(text: str) -> str:
    return html.escape(text).replace("\n", "<br/>")


def _node_inner_html(node: FlowNode) -> str:
    title = _br_escape(node.title)
    parts = [f'<span class="flow-node-title">{title}</span>']
    if node.caption:
        parts.append(
            f'<span class="flow-node-caption">{_br_escape(node.caption)}</span>'
        )
    if node.badge:
        parts.append(
            f'<span class="flow-node-badge">{_br_escape(node.badge)}</span>'
        )
    if node.chips:
        chip_html = "".join(
            f'<span class="flow-chip">{_br_escape(c)}</span>' for c in node.chips
        )
        parts.append(f'<span class="flow-chips">{chip_html}</span>')
    return "".join(parts)


def _render_node(node: FlowNode) -> str:
    kind_attr = f' data-kind="{html.escape(node.kind)}"' if node.kind else ""
    kind_class = f" flow-node-{node.kind}" if node.kind else ""
    id_attr = (
        f' data-id="{html.escape(node.node_id)}"' if node.node_id else ""
    )
    return (
        f'<div class="flow-node{kind_class}" data-node="{html.escape(node.key)}"'
        f"{kind_attr}{id_attr}>{_node_inner_html(node)}</div>"
    )


def _edge_kind(edge: FlowEdge) -> str:
    if edge.cross:
        return "link"
    if edge.bidirectional:
        return "bidirectional"
    if edge.style == "dashed":
        return "dashed"
    return "solid"


def _render_edge(edge: FlowEdge) -> str:
    classes = "flow-edge"
    if edge.cross:
        classes += " flow-edge-cross"
    label_attr = (
        f' data-label="{html.escape(edge.label)}"' if edge.label is not None else ""
    )
    bi = ' data-bidirectional="true"' if edge.bidirectional else ""
    route = f' data-route="{html.escape(edge.route)}"' if edge.cross else ""
    kind = _edge_kind(edge)
    return (
        f'<div class="{classes}" data-from="{html.escape(edge.source)}" '
        f'data-to="{html.escape(edge.target)}" data-style="{edge.style}" '
        f'data-kind="{kind}" data-pair-index="{edge.pair_index}" '
        f'data-pair-count="{edge.pair_count}"'
        f"{label_attr}{bi}{route}></div>"
    )


def _render_callout(callout: FlowCallout) -> str:
    return (
        f'<div class="flow-callout" data-anchor="{html.escape(callout.anchor)}" '
        f'data-pos="{html.escape(callout.pos)}">'
        f"{_br_escape(callout.text)}</div>"
    )


def _render_column(diagram: FlowDiagram, col: str | list[str]) -> str:
    if isinstance(col, list):
        inner = "".join(_render_node(diagram.nodes[k]) for k in col)
        return f'<div class="flow-stack">{inner}</div>'
    return _render_node(diagram.nodes[col])


def render_flow_html(diagram: FlowDiagram) -> str:
    option_classes = " ".join(sorted(f"flow-{opt}" for opt in diagram.options))
    class_attr = "flow" + (f" {option_classes}" if option_classes else "")
    parts = [f'<div class="{class_attr}">']

    multi = len(diagram.lanes) > 1 or any(lane.label for lane in diagram.lanes)
    has_stack = any(
        isinstance(col, list) for lane in diagram.lanes for col in lane.columns
    )

    if multi or has_stack:
        parts.append('<div class="flow-lanes">')
        for index, lane in enumerate(diagram.lanes):
            parts.append(f'<div class="lane" data-lane="{index}">')
            if lane.label:
                parts.append(
                    f'<div class="lane-label">{html.escape(lane.label)}</div>'
                )
            parts.append('<div class="flow-row">')
            for col in lane.columns:
                parts.append(_render_column(diagram, col))
            parts.append("</div>")  # flow-row
            for edge in lane.edges:
                parts.append(_render_edge(edge))
            parts.append("</div>")  # lane
        parts.append("</div>")  # flow-lanes
    else:
        lane = diagram.lanes[0] if diagram.lanes else FlowLane()
        for col in lane.columns:
            parts.append(_render_column(diagram, col))
        for edge in lane.edges:
            parts.append(_render_edge(edge))

    for edge in diagram.links:
        parts.append(_render_edge(edge))
    for callout in diagram.callouts:
        parts.append(_render_callout(callout))

    parts.append("</div>")
    return "\n".join(parts)


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
    for callout in diagram.callouts:
        if callout.anchor not in keys:
            keys.append(callout.anchor)
    return keys, list(diagram.errors)
