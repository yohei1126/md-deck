# Changelog

## Unreleased

### Fixed

- Fan-in / fan-out edges distribute distinct ports along the shared node side (spacing from `flow_port_gap`, default 12px) so arrowheads no longer stack on one point. Corridors stagger so parallel trunks do not share one horizontal segment. `route=between` stays orthogonal even when the source sits above the target’s width.
- Same-row edges between non-neighbouring nodes route around intermediate nodes instead of drawing a straight line through them.
- A bare `{#id} -> {#other}` that names nodes already defined in other lanes resolves those ids and draws a cross-lane link. Unknown bare ids report a clear error (with `file:line` via `md-deck check`) instead of “duplicate flow node id”.

### Changed

- `footer_inset_right` / `footer_inset_bottom` may be negative. `footer_inset_right` is still added to `page_padding_right`; a negative value pulls the footer closer to the page edge than the content padding (for example `page_padding: 40` with `footer_inset_right: -20px`). Non-negative values keep the previous layout.

### Added

- Style tokens `flow_callout_gap` and `flow_port_gap` (CSS `--flow-callout-gap`, `--flow-port-gap`; default `12px`).
- Callout option `side=top|bottom|left|right` to choose where the connector leaves the callout box (`[pos=below-left side=right]`).
