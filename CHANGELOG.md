# Changelog

## Unreleased

### Fixed

- Straight edges (`shape=straight`, `::: flow straight`, or `flow_edge_shape: straight`) no longer draw along intermediate node borders. When a straight segment would cross or run along a non-endpoint node, routing falls back to an obstacle-avoiding orthogonal path (same-row bends above/below, distinct fan-in trunks).
- Callout connectors with `pos=above|below` and a sideways `side=` that would run back through the callout box now leave the requested side and route outside the box, or fall back to the facing side.
- Callout connectors with `side=left|right` and `pos=below*` / `above` (and the mirrored `side=top|bottom` with `pos=left|right`) draw an L that leaves the callout side, runs to the anchor entry x/y, then enters the node edge with the arrowhead pointing into the node. The previous H-V-H mid path left the last segment along the node border. Geometry checks now require the final segment to be perpendicular to the edge it enters.
- Fan-in / fan-out edges distribute distinct ports along the shared node side (spacing from `flow_port_gap`, default 12px) so arrowheads no longer stack on one point. Corridors stagger so parallel trunks do not share one horizontal segment. `route=between` stays orthogonal even when the source sits above the target’s width.
- Same-row edges between non-neighbouring nodes route around intermediate nodes instead of drawing a straight line through them.
- A bare `{#id} -> {#other}` that names nodes already defined in other lanes resolves those ids and draws a cross-lane link. Unknown bare ids report a clear error (with `file:line` via `md-deck check`) instead of “duplicate flow node id”.

### Changed

- `footer_inset_right` / `footer_inset_bottom` may be negative. `footer_inset_right` is still added to `page_padding_right`; a negative value pulls the footer closer to the page edge than the content padding (for example `page_padding: 40` with `footer_inset_right: -20px`). Non-negative values keep the previous layout.
- Footer source lines still strip the `Source:` / `出典：` marker from the Markdown line. The visible prefix is now `label_source` (defaults: `Source:` for `en`, `出典：` for `ja`). Set `label_source: ""` to keep the previous stripped-only footer text.

### Added

- Style tokens `source_label_weight` (CSS `--source-label-weight`, default `600`) and `source_label_gap` (CSS `--source-label-gap`, default `0.15em`) for `.slide-footer .source .label`. Set `source_label_weight: 400` and `source_label_gap: 0` for a plain prefix with no extra gap.
- Style tokens `flow_callout_gap` and `flow_port_gap` (CSS `--flow-callout-gap`, `--flow-port-gap`; default `12px`).
- Callout option `side=top|bottom|left|right` to choose where the connector leaves the callout box (`[pos=below-left side=right]`).
- Style token `label_source` (CSS `--label-source`) for the footer `.source .label` prefix. Empty string hides the prefix.
- Opt-in straight / diagonal edges: per-edge `shape=straight` on `link:` or a chain destination (`A -> B [shape=straight]`), flow option `::: flow straight`, or style token `flow_edge_shape: orthogonal|straight`. Straight edges still use distributed ports (`flow_port_gap`). Orthogonal remains the default.
