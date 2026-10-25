"""Playwright geometry regressions for flow routing and shrink-to-fit."""

from __future__ import annotations

from pathlib import Path

import pytest

from md_deck.build import build_html, render_pdf
from md_deck.flow import parse_flow_body
from md_deck.slides import parse_deck
from md_deck.style import load_style_file, tokens_to_css

FIX = Path(__file__).parent / "fixtures" / "geometry"

# Shared JS: path segments vs node boxes (layout space).
# pad expands the box so segments that cross OR run along a border count as hits.
HIT_JS = r"""
({ slideIndex, fromKey, toKey, avoidKeys }) => {
  const slide = document.querySelectorAll('.slide')[slideIndex];
  const flow = slide.querySelector('.flow');
  const scale = Number(slide.dataset.scale || '1') || 1;
  const flowRect = flow.getBoundingClientRect();
  const path = flow.querySelector(
    `svg.flow-svg path.flow-arrow[data-from="${fromKey}"][data-to="${toKey}"]`
  );
  if (!path) return { ok: false, reason: 'missing-path' };
  const d = path.getAttribute('d') || '';
  const pts = [];
  const re = /([ML])\s*([-\d.]+)\s+([-\d.]+)/g;
  let m;
  while ((m = re.exec(d))) {
    pts.push({ x: parseFloat(m[2]), y: parseFloat(m[3]) });
  }
  function box(el) {
    const r = el.getBoundingClientRect();
    return {
      left: (r.left - flowRect.left) / scale,
      right: (r.right - flowRect.left) / scale,
      top: (r.top - flowRect.top) / scale,
      bottom: (r.bottom - flowRect.top) / scale,
    };
  }
  const avoid = new Set(avoidKeys || []);
  const nodes = Array.from(flow.querySelectorAll('.flow-node'))
    .filter((el) => avoid.has(el.getAttribute('data-node')))
    .map((el) => ({ key: el.getAttribute('data-node'), box: box(el) }));
  const pad = 3;
  function lineHitsRect(p, q, r) {
    let t0 = 0, t1 = 1;
    const dx = q.x - p.x, dy = q.y - p.y;
    const clips = [[-dx, p.x - r.left], [dx, r.right - p.x], [-dy, p.y - r.top], [dy, r.bottom - p.y]];
    for (const [a, b] of clips) {
      if (Math.abs(a) < 1e-9) { if (b < 0) return false; continue; }
      const t = b / a;
      if (a < 0) { if (t > t1) return false; if (t > t0) t0 = t; }
      else { if (t < t0) return false; if (t < t1) t1 = t; }
    }
    return t1 >= t0;
  }
  function segHits(p, q, b) {
    const minX = Math.min(p.x, q.x), maxX = Math.max(p.x, q.x);
    const minY = Math.min(p.y, q.y), maxY = Math.max(p.y, q.y);
    const bl = b.left - pad, br = b.right + pad, bt = b.top - pad, bb = b.bottom + pad;
    if (maxX < bl || minX > br || maxY < bt || minY > bb) return false;
    if (Math.abs(p.x - q.x) < 0.75) return p.x >= bl && p.x <= br;
    if (Math.abs(p.y - q.y) < 0.75) return p.y >= bt && p.y <= bb;
    return lineHitsRect(p, q, { left: bl, right: br, top: bt, bottom: bb });
  }
  const hits = [];
  for (let i = 1; i < pts.length; i++) {
    for (const n of nodes) {
      if (segHits(pts[i - 1], pts[i], n.box)) hits.push(n.key);
    }
  }
  return { ok: hits.length === 0, hits: [...new Set(hits)], pts };
}
"""


@pytest.fixture(scope="module")
def geometry_page(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("geometry")
    pdf = out_dir / "g.pdf"
    html_path = out_dir / "g.html"
    text = (FIX / "slides.md").read_text(encoding="utf-8")
    tokens, style_extra = load_style_file(FIX / "deck_style.md")
    theme_css = tokens_to_css(tokens, style_extra)
    meta, slides = parse_deck(text, style_tokens=tokens)
    html = build_html(
        slides,
        theme_css,
        [],
        str(meta.get("title") or "geometry"),
        lang=str(meta.get("lang") or "en"),
        page_number_placement=str(tokens.get("page_number_placement") or "bottom-right"),
    )
    html_path.write_text(html, encoding="utf-8")
    render_pdf(html, pdf, png_dir=None, fail_on_overflow=False)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1280, "height": 720},
            device_scale_factor=1,
        )
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.wait_for_function("() => window.__mdDeckReady === true")
        yield page
        browser.close()


def test_parse_separate_lines_and_chips():
    """Parse coverage matching tests/fixtures/geometry/slides.md shapes."""
    d = parse_flow_body(
        "lane: Top\nP {#p}\nQ {#q}\nR {#r}\nlane: Bottom\nTarget {#t}\n"
        "link: p => t\nlink: q => t\nlink: r => t\n"
    )
    assert d.lanes[0].edges == []
    assert len(d.links) == 3

    chips = parse_flow_body("A -> [[x, y]] -> B\nN [[a/b, c]] -> M\n")
    assert chips.errors == []
    chip_node = next(n for n in chips.nodes.values() if n.chips == ["x", "y"])
    assert chip_node.title == ""
    n_node = chips.nodes["N"]
    assert n_node.chips == ["a/b", "c"]


def test_vertical_down_route_avoids_nodes(geometry_page):
    result = geometry_page.evaluate(
        HIT_JS,
        {
            "slideIndex": 0,
            "fromKey": "a3",
            "toKey": "b1",
            "avoidKeys": ["A1", "A2", "B2", "B3"],
        },
    )
    assert "B3" not in result.get("hits", []), result
    assert not result.get("hits"), result


def test_fan_in_auto_avoids_nodes_and_no_chain(geometry_page):
    # No in-lane chain edges between P/Q/R.
    chained = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[1];
          const edges = Array.from(slide.querySelectorAll('.flow-edge:not(.flow-edge-cross)'));
          return edges.map((e) => [e.dataset.from, e.dataset.to]);
        }"""
    )
    assert chained == []

    meta = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[1];
          const flow = slide.querySelector('.flow');
          const scale = Number(slide.dataset.scale || '1') || 1;
          const fr = flow.getBoundingClientRect();
          const t = flow.querySelector('.flow-node[data-node="t"]').getBoundingClientRect();
          const top = (t.top - fr.top) / scale;
          const paths = {};
          flow.querySelectorAll('path.flow-link').forEach((p) => {
            paths[p.dataset.from] = p.getAttribute('d');
          });
          return { top, paths, flowW: flow.clientWidth };
        }"""
    )

    for src in ("p", "q", "r"):
        result = geometry_page.evaluate(
            HIT_JS,
            {
                "slideIndex": 1,
                "fromKey": src,
                "toKey": "t",
                "avoidKeys": ["p", "q", "r", "t"],
            },
        )
        foreign = [k for k in result.get("hits", []) if k not in {src, "t"}]
        assert not foreign, (src, result)
        xs = [p["x"] for p in result.get("pts", [])]
        assert xs and min(xs) >= -1, (src, result)
        assert max(xs) <= meta["flowW"] + 1, (src, result)
        # Enter the target from the top (last point near target top centre).
        end = result["pts"][-1]
        assert abs(end["y"] - meta["top"]) < 2.5, (src, end, meta["top"])


def test_multiline_label_box_clears_arrow(geometry_page):
    result = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[2];
          const flow = slide.querySelector('.flow');
          const scale = Number(slide.dataset.scale || '1') || 1;
          const flowRect = flow.getBoundingClientRect();
          const path = flow.querySelector('path.flow-arrow[data-from="s"][data-to="t"]:not(.flow-arrow-dashed)');
          const label = flow.querySelector('text.flow-label[data-from="s"][data-to="t"]');
          if (!path || !label) return { ok: false, reason: 'missing' };
          const pb = path.getBBox();
          const lb = label.getBBox();
          // Label box should sit entirely above or below the stroke midline.
          const midY = pb.y + pb.height / 2;
          const above = lb.y + lb.height <= midY - 2;
          const below = lb.y >= midY + 2;
          const s = flow.querySelector('.flow-node[data-node="s"]');
          const t = flow.querySelector('.flow-node[data-node="t"]');
          const sr = s.getBoundingClientRect();
          const tr = t.getBoundingClientRect();
          const gap = (tr.left - sr.right) / scale;
          return { ok: above || below, above, below, gap, labelW: lb.width };
        }"""
    )
    assert result["ok"], result
    assert result["gap"] >= result["labelW"] - 1, result


def test_stack_edges_attach_midbox(geometry_page):
    result = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[3];
          const flow = slide.querySelector('.flow');
          const scale = Number(slide.dataset.scale || '1') || 1;
          const flowRect = flow.getBoundingClientRect();
          const stack = flow.querySelector('.flow-stack');
          const sb = stack.getBoundingClientRect();
          const stackBox = {
            left: (sb.left - flowRect.left) / scale,
            right: (sb.right - flowRect.left) / scale,
            top: (sb.top - flowRect.top) / scale,
            bottom: (sb.bottom - flowRect.top) / scale,
            cy: ((sb.top + sb.bottom) / 2 - flowRect.top) / scale,
            cx: ((sb.left + sb.right) / 2 - flowRect.left) / scale,
          };
          function endPoint(d, which) {
            const pts = [];
            const re = /([ML])\\s*([-\\d.]+)\\s+([-\\d.]+)/g;
            let m;
            while ((m = re.exec(d))) pts.push({ x: +m[2], y: +m[3] });
            return which === 'start' ? pts[0] : pts[pts.length - 1];
          }
          const inPath = flow.querySelector('path.flow-arrow[data-from="L"][data-to="Up"]');
          const outPath = flow.querySelector('path.flow-arrow[data-from="Up"][data-to="R"]');
          const inEnd = endPoint(inPath.getAttribute('d'), 'end');
          const outStart = endPoint(outPath.getAttribute('d'), 'start');
          return {
            stackCy: stackBox.cy,
            inEnd,
            outStart,
            inNearMid: Math.abs(inEnd.y - stackBox.cy) < stackBox.bottom - stackBox.top,
            // Attachment should be near vertical mid of the stack, not the top node only.
            inDyFromMid: Math.abs(inEnd.y - stackBox.cy),
            outDyFromMid: Math.abs(outStart.y - stackBox.cy),
            halfH: (stackBox.bottom - stackBox.top) / 2,
          };
        }"""
    )
    assert result["inDyFromMid"] <= result["halfH"] * 0.35, result
    assert result["outDyFromMid"] <= result["halfH"] * 0.35, result


def test_callout_arrow_points_at_node_and_hooks(geometry_page):
    result = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[2];
          const flow = slide.querySelector('.flow');
          const scale = Number(slide.dataset.scale || '1') || 1;
          const flowRect = flow.getBoundingClientRect();
          const path = flow.querySelector('path.flow-callout-arrow');
          const node = flow.querySelector('.flow-node[data-node="t"]');
          const callout = flow.querySelector('div.flow-callout');
          if (!path || !node || !callout) return { ok: false };
          const d = path.getAttribute('d') || '';
          const pts = [];
          const re = /([ML])\\s*([-\\d.]+)\\s+([-\\d.]+)/g;
          let m;
          while ((m = re.exec(d))) pts.push({ x: +m[2], y: +m[3] });
          const end = pts[pts.length - 1];
          const nb = node.getBoundingClientRect();
          const nodeBottom = {
            x: ((nb.left + nb.right) / 2 - flowRect.left) / scale,
            y: (nb.bottom - flowRect.top) / scale,
          };
          const cb = callout.getBoundingClientRect();
          const calloutBox = {
            left: (cb.left - flowRect.left) / scale,
            right: (cb.right - flowRect.left) / scale,
            top: (cb.top - flowRect.top) / scale,
            bottom: (cb.bottom - flowRect.top) / scale,
          };
          const slideRect = flow.closest('.slide').getBoundingClientRect();
          const cbPage = callout.getBoundingClientRect();
          return {
            hasFlowLink: path.classList.contains('flow-link'),
            hasFlowCallout: path.classList.contains('flow-callout'),
            endNearNode: Math.hypot(end.x - nodeBottom.x, end.y - nodeBottom.y) < 8,
            // Horizontal clamp keeps notes on-slide; vertical may extend the flow box.
            clamped: calloutBox.left >= -1
              && calloutBox.right <= flow.clientWidth + 1
              && cbPage.left >= slideRect.left - 1
              && cbPage.right <= slideRect.right + 1,
          };
        }"""
    )
    assert result["hasFlowLink"]
    assert result["hasFlowCallout"]
    assert result["endNearNode"], result
    assert result["clamped"], result


def test_single_lane_dom_wrappers(geometry_page):
    result = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[3];
          const flow = slide.querySelector('.flow');
          return {
            lanes: !!flow.querySelector('.flow-lanes'),
            lane: !!flow.querySelector('.lane'),
            row: !!flow.querySelector('.flow-row'),
          };
        }"""
    )
    assert result == {"lanes": True, "lane": True, "row": True}


def test_chips_only_renders(geometry_page):
    result = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[4];
          const chips = Array.from(slide.querySelectorAll('.flow-chip')).map((c) => c.textContent);
          return chips;
        }"""
    )
    assert "x" in result and "y" in result
    assert "a/b" in result and "c" in result
    assert result.count("a") == 0 or "a/b" in result


def test_shrink_honours_last_margin(geometry_page):
    result = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[5];
          const inner = slide.querySelector('.slide-inner');
          const content = slide.querySelector('.slide-content');
          const q = content.querySelector('.question');
          const style = getComputedStyle(q);
          const mb = parseFloat(style.marginBottom) || 0;
          const bottom = q.offsetTop + q.offsetHeight + mb;
          return {
            overflow: slide.dataset.overflow || null,
            bottom,
            innerH: inner.clientHeight,
            fits: bottom <= inner.clientHeight + 0.5,
            marginBottom: mb,
          };
        }"""
    )
    assert result["marginBottom"] >= 39
    assert result["fits"], result
    assert result["overflow"] is None


def test_footer_inset_token_emitted():
    tokens, extra = load_style_file(FIX / "deck_style.md")
    css = tokens_to_css(tokens, extra)
    assert "--footer-inset-bottom:" in css
    assert "--footer-inset-right:" in css
    assert "--flow-callout-gap:" in css
    assert "--flow-port-gap:" in css


def _path_pts(page, slide_index, from_key, to_key):
    return page.evaluate(
        """({ slideIndex, fromKey, toKey }) => {
          const slide = document.querySelectorAll('.slide')[slideIndex];
          const path = slide.querySelector(
            `svg.flow-svg path.flow-arrow[data-from="${fromKey}"][data-to="${toKey}"]`
          );
          if (!path) return null;
          const pts = [];
          const re = /([ML])\\s*([-\\d.]+)\\s+([-\\d.]+)/g;
          let m;
          const d = path.getAttribute('d') || '';
          while ((m = re.exec(d))) pts.push({ x: +m[2], y: +m[3] });
          return pts;
        }""",
        {"slideIndex": slide_index, "fromKey": from_key, "toKey": to_key},
    )


def _is_orthogonal(pts):
    for i in range(1, len(pts)):
        dx = abs(pts[i]["x"] - pts[i - 1]["x"])
        dy = abs(pts[i]["y"] - pts[i - 1]["y"])
        if dx >= 0.75 and dy >= 0.75:
            return False
    return True


def test_fan_in_ports_distributed_and_orthogonal(geometry_page):
    meta = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[6];
          const flow = slide.querySelector('.flow');
          const scale = Number(slide.dataset.scale || '1') || 1;
          const fr = flow.getBoundingClientRect();
          const t = flow.querySelector('.flow-node[data-node="t7"]').getBoundingClientRect();
          return {
            top: (t.top - fr.top) / scale,
            left: (t.left - fr.left) / scale,
            right: (t.right - fr.left) / scale,
            cx: ((t.left + t.right) / 2 - fr.left) / scale,
          };
        }"""
    )
    ends = []
    mid_ys = []
    for src in ("p7", "q7", "r7"):
        pts = _path_pts(geometry_page, 6, src, "t7")
        assert pts and len(pts) >= 2, src
        assert _is_orthogonal(pts), (src, pts)
        end = pts[-1]
        assert abs(end["y"] - meta["top"]) < 2.5, (src, end, meta)
        assert meta["left"] - 1 <= end["x"] <= meta["right"] + 1, (src, end, meta)
        ends.append(end["x"])
        if len(pts) >= 4:
            mid_ys.append(pts[1]["y"])
        hit = geometry_page.evaluate(
            HIT_JS,
            {
                "slideIndex": 6,
                "fromKey": src,
                "toKey": "t7",
                "avoidKeys": ["p7", "q7", "r7", "t7"],
            },
        )
        foreign = [k for k in hit.get("hits", []) if k not in {src, "t7"}]
        assert not foreign, (src, hit)
    # Distinct entry ports along the target top.
    assert max(ends) - min(ends) >= 10, ends
    assert len(set(round(x, 1) for x in ends)) >= 2, ends
    # Shared trunks should not collapse to one horizontal y for all three.
    if len(mid_ys) >= 3:
        assert max(mid_ys) - min(mid_ys) >= 8 or len(set(round(y, 1) for y in mid_ys)) >= 2, mid_ys


def test_same_row_edges_skip_intermediate_nodes(geometry_page):
    for src, avoid in (
        ("p8", ["q8", "r8"]),
        ("q8", ["p8", "r8"]),
        ("r8", ["p8", "q8"]),
    ):
        result = geometry_page.evaluate(
            HIT_JS,
            {
                "slideIndex": 7,
                "fromKey": src,
                "toKey": "t8",
                "avoidKeys": avoid,
            },
        )
        assert result.get("ok"), (src, result)
        pts = result.get("pts") or []
        assert _is_orthogonal(pts), (src, pts)


def test_cross_lane_id_arrow_renders_link(geometry_page):
    result = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[8];
          const flow = slide.querySelector('.flow');
          const path = flow.querySelector('path.flow-arrow[data-from="a9"][data-to="b9"]');
          const nodes = Array.from(flow.querySelectorAll('.flow-node')).map(
            (n) => n.getAttribute('data-node')
          );
          return {
            hasPath: !!path,
            isLink: path ? path.classList.contains('flow-link') : false,
            nodes,
          };
        }"""
    )
    assert result["hasPath"]
    assert result["isLink"]
    assert result["nodes"].count("a9") == 1
    assert result["nodes"].count("b9") == 1


def test_callout_side_exits_from_requested_side(geometry_page):
    result = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[9];
          const flow = slide.querySelector('.flow');
          const scale = Number(slide.dataset.scale || '1') || 1;
          const fr = flow.getBoundingClientRect();
          const callout = flow.querySelector('div.flow-callout');
          const path = flow.querySelector('path.flow-callout-arrow');
          const node = flow.querySelector('.flow-node[data-node="r10"]');
          if (!callout || !path || !node) return { ok: false };
          const pts = [];
          const re = /([ML])\\s*([-\\d.]+)\\s+([-\\d.]+)/g;
          let m;
          const d = path.getAttribute('d') || '';
          while ((m = re.exec(d))) pts.push({ x: +m[2], y: +m[3] });
          const cb = callout.getBoundingClientRect();
          const box = {
            right: (cb.right - fr.left) / scale,
            cy: ((cb.top + cb.bottom) / 2 - fr.top) / scale,
          };
          const nb = node.getBoundingClientRect();
          const nodeBottom = {
            x: ((nb.left + nb.right) / 2 - fr.left) / scale,
            y: (nb.bottom - fr.top) / scale,
          };
          const start = pts[0];
          const end = pts[pts.length - 1];
          const prev = pts[pts.length - 2];
          // Final segment must be vertical into the bottom edge (not along it).
          const finalDx = Math.abs(end.x - prev.x);
          const finalDy = Math.abs(end.y - prev.y);
          return {
            ok: true,
            side: callout.getAttribute('data-side'),
            startNearRight:
              Math.abs(start.x - box.right) < 3 && Math.abs(start.y - box.cy) < 8,
            endNearBottom:
              Math.hypot(end.x - nodeBottom.x, end.y - nodeBottom.y) < 8,
            finalPerpendicular: finalDx < 0.75 && finalDy > 2,
            entersUpward: prev.y > end.y + 1,
            pts,
          };
        }"""
    )
    assert result["ok"]
    assert result["side"] == "right"
    assert result["startNearRight"], result
    assert result["endNearBottom"], result
    assert result["finalPerpendicular"], result
    assert result["entersUpward"], result


def test_callout_side_left_below_right_l_shape(geometry_page):
    result = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[10];
          const flow = slide.querySelector('.flow');
          const scale = Number(slide.dataset.scale || '1') || 1;
          const fr = flow.getBoundingClientRect();
          const callout = flow.querySelector('div.flow-callout');
          const path = flow.querySelector('path.flow-callout-arrow');
          const node = flow.querySelector('.flow-node[data-node="a11"]');
          if (!callout || !path || !node) return { ok: false };
          const pts = [];
          const re = /([ML])\\s*([-\\d.]+)\\s+([-\\d.]+)/g;
          let m;
          const d = path.getAttribute('d') || '';
          while ((m = re.exec(d))) pts.push({ x: +m[2], y: +m[3] });
          const cb = callout.getBoundingClientRect();
          const box = {
            left: (cb.left - fr.left) / scale,
            cy: ((cb.top + cb.bottom) / 2 - fr.top) / scale,
          };
          const nb = node.getBoundingClientRect();
          const nodeBottom = {
            x: ((nb.left + nb.right) / 2 - fr.left) / scale,
            y: (nb.bottom - fr.top) / scale,
          };
          const start = pts[0];
          const end = pts[pts.length - 1];
          const prev = pts[pts.length - 2];
          const finalDx = Math.abs(end.x - prev.x);
          const finalDy = Math.abs(end.y - prev.y);
          // L-shape: three points (or simplified), not a Z along the border.
          return {
            ok: true,
            side: callout.getAttribute('data-side'),
            startNearLeft:
              Math.abs(start.x - box.left) < 3 && Math.abs(start.y - box.cy) < 8,
            endNearBottom:
              Math.hypot(end.x - nodeBottom.x, end.y - nodeBottom.y) < 8,
            finalPerpendicular: finalDx < 0.75 && finalDy > 2,
            entersUpward: prev.y > end.y + 1,
            pointCount: pts.length,
            pts,
          };
        }"""
    )
    assert result["ok"]
    assert result["side"] == "left"
    assert result["startNearLeft"], result
    assert result["endNearBottom"], result
    assert result["finalPerpendicular"], result
    assert result["entersUpward"], result
    assert result["pointCount"] <= 3, result


def test_straight_flow_fan_in_uses_ports(geometry_page):
    meta = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[11];
          const flow = slide.querySelector('.flow');
          const scale = Number(slide.dataset.scale || '1') || 1;
          const fr = flow.getBoundingClientRect();
          const t = flow.querySelector('.flow-node[data-node="t12"]').getBoundingClientRect();
          return {
            isStraightFlow: flow.classList.contains('flow-straight'),
            top: (t.top - fr.top) / scale,
            left: (t.left - fr.left) / scale,
            right: (t.right - fr.left) / scale,
          };
        }"""
    )
    assert meta["isStraightFlow"]
    ends = []
    for src in ("p12", "q12", "r12"):
        pts = _path_pts(geometry_page, 11, src, "t12")
        assert pts and len(pts) == 2, (src, pts)
        # Diagonal / straight: both dx and dy non-trivial for outer edges,
        # or at least not forced orthogonal for the whole path set.
        end = pts[-1]
        assert abs(end["y"] - meta["top"]) < 2.5, (src, end, meta)
        assert meta["left"] - 1 <= end["x"] <= meta["right"] + 1, (src, end, meta)
        ends.append(end["x"])
        shape = geometry_page.evaluate(
            """({ slideIndex, fromKey, toKey }) => {
              const slide = document.querySelectorAll('.slide')[slideIndex];
              const path = slide.querySelector(
                `svg.flow-svg path.flow-arrow[data-from="${fromKey}"][data-to="${toKey}"]`
              );
              return path ? path.getAttribute('data-shape') : null;
            }""",
            {"slideIndex": 11, "fromKey": src, "toKey": "t12"},
        )
        assert shape == "straight", (src, shape)
    assert max(ends) - min(ends) >= 10, ends


def test_per_edge_straight_shape_mixed_with_orthogonal(geometry_page):
    straight = _path_pts(geometry_page, 12, "p13", "t13")
    ortho = _path_pts(geometry_page, 12, "q13", "t13")
    assert straight and len(straight) == 2, straight
    assert ortho and len(ortho) >= 2, ortho
    assert not _is_orthogonal(straight) or len(straight) == 2
    # Orthogonal peer still bends (or is colinear); straight is a single segment.
    assert _is_orthogonal(ortho), ortho
    shapes = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[12];
          const flow = slide.querySelector('.flow');
          return {
            p: flow.querySelector('path.flow-arrow[data-from="p13"][data-to="t13"]')
              ?.getAttribute('data-shape'),
            q: flow.querySelector('path.flow-arrow[data-from="q13"][data-to="t13"]')
              ?.getAttribute('data-shape'),
          };
        }"""
    )
    assert shapes["p"] == "straight"
    assert shapes["q"] == "orthogonal"


def test_negative_footer_inset_accepted_and_emitted():
    from md_deck.validate import check_deck

    errors = check_deck(FIX / "slides_footer.md")
    assert errors == [], errors
    tokens, extra = load_style_file(FIX / "deck_style_footer.md")
    css = tokens_to_css(tokens, extra)
    assert "--footer-inset-right: -20px;" in css


def test_straight_same_row_skips_intermediate_borders(geometry_page):
    result = geometry_page.evaluate(
        HIT_JS,
        {
            "slideIndex": 13,
            "fromKey": "a14",
            "toKey": "d14",
            "avoidKeys": ["b14", "c14"],
        },
    )
    assert result.get("ok"), result
    pts = result.get("pts") or []
    assert len(pts) >= 3, pts  # must bend; not a border-hugging chord


def test_straight_fan_in_same_row_avoids_borders_and_diverges(geometry_page):
    mid_ys = []
    drops = []
    paths = {}
    for src, avoid in (
        ("x15", ["y15", "z15"]),
        ("y15", ["x15", "z15"]),
        ("z15", ["x15", "y15"]),
    ):
        hit = geometry_page.evaluate(
            HIT_JS,
            {
                "slideIndex": 14,
                "fromKey": src,
                "toKey": "t15",
                "avoidKeys": avoid,
            },
        )
        assert hit.get("ok"), (src, hit)
        pts = hit.get("pts") or []
        assert pts, src
        paths[src] = pts
        # U-shaped detours only (direct same-row neighbours stay 2-point).
        if len(pts) < 4:
            continue
        for i in range(1, len(pts)):
            if abs(pts[i]["y"] - pts[i - 1]["y"]) < 0.75 and abs(
                pts[i]["x"] - pts[i - 1]["x"]
            ) >= 8:
                mid_ys.append(round(pts[i]["y"], 1))
                drops.append(abs(pts[-1]["y"] - pts[i]["y"]))
                break
    # Fan-in edges that detour must not collapse onto one shared trunk.
    assert len(mid_ys) >= 2, paths
    assert max(mid_ys) - min(mid_ys) >= 16, mid_ys
    assert min(drops) >= 18, drops
    # Farther source (x15) must take the farther drop port so trunks nest.
    assert paths["x15"][-1]["x"] > paths["y15"][-1]["x"], (
        paths["x15"],
        paths["y15"],
    )
    # Detour fan-in ports stay at least an arrowhead-width apart.
    ends = [paths[s][-1]["x"] for s in ("x15", "y15") if len(paths[s]) >= 4]
    if len(ends) >= 2:
        assert abs(ends[0] - ends[1]) >= 16, ends

    # Nested trunks must not cross near the arrowheads (tight endpoint tolerance).
    cross = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[14];
          const flow = slide.querySelector('.flow');
          function ptsOf(fromKey) {
            const path = flow.querySelector(
              `svg.flow-svg path.flow-arrow[data-from="${fromKey}"][data-to="t15"]`
            );
            if (!path) return null;
            const pts = [];
            const re = /([ML])\\s*([-\\d.]+)\\s+([-\\d.]+)/g;
            let m;
            const d = path.getAttribute('d') || '';
            while ((m = re.exec(d))) pts.push({ x: +m[2], y: +m[3] });
            return pts;
          }
          function segmentsCross(a1, a2, b1, b2) {
            const eps = 0.75;
            const aVert = Math.abs(a1.x - a2.x) < eps;
            const bVert = Math.abs(b1.x - b2.x) < eps;
            if (aVert === bVert) return false;
            const vert = aVert ? [a1, a2] : [b1, b2];
            const horz = aVert ? [b1, b2] : [a1, a2];
            const x = vert[0].x;
            const y = horz[0].y;
            const yLo = Math.min(vert[0].y, vert[1].y) + eps;
            const yHi = Math.max(vert[0].y, vert[1].y) - eps;
            const xLo = Math.min(horz[0].x, horz[1].x) + eps;
            const xHi = Math.max(horz[0].x, horz[1].x) - eps;
            return x > xLo && x < xHi && y > yLo && y < yHi;
          }
          function near(p, q, tol) {
            return Math.hypot(p.x - q.x, p.y - q.y) <= tol;
          }
          const a = ptsOf('x15');
          const b = ptsOf('y15');
          if (!a || !b) return { ok: false };
          let crosses = 0;
          let nearEnd = 0;
          for (let i = 1; i < a.length; i++) {
            for (let j = 1; j < b.length; j++) {
              if (!segmentsCross(a[i - 1], a[i], b[j - 1], b[j])) continue;
              crosses += 1;
              const crossPt =
                Math.abs(a[i - 1].x - a[i].x) < 0.75
                  ? { x: a[i - 1].x, y: b[j - 1].y }
                  : { x: b[j - 1].x, y: a[i - 1].y };
              // Only ignore exact shared endpoints (~1px). An 8px exclusion
              // would hide the nested-trunk crossing next to the arrowheads.
              const ends = [a[0], a[a.length - 1], b[0], b[b.length - 1]];
              if (ends.some((e) => near(crossPt, e, 1.5))) nearEnd += 1;
              else return { ok: false, crosses, crossPt, a, b };
            }
          }
          return { ok: true, crosses, nearEnd, a, b };
        }"""
    )
    assert cross.get("ok"), cross


def test_callout_above_side_left_avoids_own_box(geometry_page):
    result = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[15];
          const flow = slide.querySelector('.flow');
          const scale = Number(slide.dataset.scale || '1') || 1;
          const fr = flow.getBoundingClientRect();
          const callout = flow.querySelector('div.flow-callout');
          const path = flow.querySelector('path.flow-callout-arrow');
          const node = flow.querySelector('.flow-node[data-node="a16"]');
          if (!callout || !path || !node) return { ok: false };
          const pts = [];
          const re = /([ML])\\s*([-\\d.]+)\\s+([-\\d.]+)/g;
          let m;
          const d = path.getAttribute('d') || '';
          while ((m = re.exec(d))) pts.push({ x: +m[2], y: +m[3] });
          const cb = callout.getBoundingClientRect();
          const box = {
            left: (cb.left - fr.left) / scale,
            right: (cb.right - fr.left) / scale,
            top: (cb.top - fr.top) / scale,
            bottom: (cb.bottom - fr.top) / scale,
            cx: ((cb.left + cb.right) / 2 - fr.left) / scale,
            cy: ((cb.top + cb.bottom) / 2 - fr.top) / scale,
          };
          const inset = 2;
          const inner = {
            left: box.left + inset,
            right: box.right - inset,
            top: box.top + inset,
            bottom: box.bottom - inset,
          };
          function segHits(p, q, b) {
            const minX = Math.min(p.x, q.x), maxX = Math.max(p.x, q.x);
            const minY = Math.min(p.y, q.y), maxY = Math.max(p.y, q.y);
            if (maxX < b.left || minX > b.right || maxY < b.top || minY > b.bottom) {
              return false;
            }
            if (Math.abs(p.x - q.x) < 0.75) return p.x >= b.left && p.x <= b.right;
            if (Math.abs(p.y - q.y) < 0.75) return p.y >= b.top && p.y <= b.bottom;
            return true;
          }
          let through = false;
          for (let i = 1; i < pts.length; i++) {
            if (segHits(pts[i - 1], pts[i], inner)) through = true;
          }
          const nb = node.getBoundingClientRect();
          const nodeTop = {
            x: ((nb.left + nb.right) / 2 - fr.left) / scale,
            y: (nb.top - fr.top) / scale,
          };
          const start = pts[0];
          const end = pts[pts.length - 1];
          const prev = pts[pts.length - 2];
          const finalDx = Math.abs(end.x - prev.x);
          const finalDy = Math.abs(end.y - prev.y);
          const leftExit =
            Math.abs(start.x - box.left) < 3 && Math.abs(start.y - box.cy) < 8;
          const bottomExit =
            Math.abs(start.y - box.bottom) < 3 && Math.abs(start.x - box.cx) < 8;
          return {
            ok: true,
            through,
            leftExit,
            bottomExit,
            endNearTop: Math.hypot(end.x - nodeTop.x, end.y - nodeTop.y) < 8,
            finalPerpendicular: finalDx < 0.75 && finalDy > 2,
            entersDownward: prev.y < end.y - 1,
            pts,
          };
        }"""
    )
    assert result["ok"]
    assert not result["through"], result
    assert result["leftExit"] or result["bottomExit"], result
    assert result["endNearTop"], result
    assert result["finalPerpendicular"], result
    assert result["entersDownward"], result


def test_callout_final_segment_perpendicular_all_pos_side(geometry_page):
    # Slides 16..39 in fixtures/geometry/slides.md cover every pos/side pair.
    # Later slides are unrelated repros; keep the matrix window fixed.
    result = geometry_page.evaluate(
        """() => {
          const slides = Array.from(document.querySelectorAll('.slide'));
          const failures = [];
          const seen = [];
          const enterOf = {
            above: 'top',
            below: 'bottom',
            'below-left': 'bottom',
            'below-right': 'bottom',
            left: 'left',
            right: 'right',
          };
          const MATRIX_START = 16;
          const MATRIX_COUNT = 24;
          for (let idx = MATRIX_START; idx < MATRIX_START + MATRIX_COUNT; idx++) {
            const slide = slides[idx];
            const flow = slide && slide.querySelector('.flow');
            const callout = flow && flow.querySelector('div.flow-callout');
            const path = flow && flow.querySelector('path.flow-callout-arrow');
            if (!callout || !path) {
              failures.push({ idx, reason: 'missing' });
              continue;
            }
            const pos = callout.getAttribute('data-pos') || '';
            const side = callout.getAttribute('data-side') || '';
            seen.push(pos + ':' + side);
            const enter = enterOf[pos];
            const pts = [];
            const re = /([ML])\\s*([-\\d.]+)\\s+([-\\d.]+)/g;
            let m;
            const d = path.getAttribute('d') || '';
            while ((m = re.exec(d))) pts.push({ x: +m[2], y: +m[3] });
            if (pts.length < 2) {
              failures.push({ idx, pos, side, reason: 'short', pts });
              continue;
            }
            const prev = pts[pts.length - 2];
            const end = pts[pts.length - 1];
            const dx = Math.abs(end.x - prev.x);
            const dy = Math.abs(end.y - prev.y);
            const finalLen = Math.hypot(dx, dy);
            const ok =
              enter === 'top' || enter === 'bottom'
                ? dx < 0.75 && dy > 2
                : dy < 0.75 && dx > 2;
            if (!ok) failures.push({ idx, pos, side, enter, dx, dy, pts });
            else if (finalLen < 17.5) {
              failures.push({
                idx,
                pos,
                side,
                reason: 'short-final',
                finalLen,
                pts,
              });
            }
          }
          return { matrixCount: MATRIX_COUNT, seen, failures };
        }"""
    )
    assert result["matrixCount"] == 24, result
    assert len(result["seen"]) == 24, result
    assert result["failures"] == [], result


def test_source_label_style_tokens_emitted():
    tokens, extra = load_style_file(FIX / "deck_style.md")
    css = tokens_to_css(
        {**tokens, "source_label_weight": 400, "source_label_gap": 0},
        extra,
    )
    assert "--source-label-weight: 400;" in css
    assert "--source-label-gap: 0px;" in css
    default_css = tokens_to_css(tokens, extra)
    assert "--source-label-weight: 600;" in default_css
    assert "--source-label-gap: 0.15em;" in default_css


def _detour_trunk_meta(geometry_page, slide_index, sources, target):
    return geometry_page.evaluate(
        """({ slideIndex, sources, target }) => {
          const slide = document.querySelectorAll('.slide')[slideIndex];
          const flow = slide.querySelector('.flow');
          const scale = Number(slide.dataset.scale || '1') || 1;
          const fr = flow.getBoundingClientRect();
          const h1 = slide.querySelector('h1');
          const hr = h1.getBoundingClientRect();
          // Title and anything outside the flow box count as obstacles.
          const outside = {
            left: -1e6,
            right: 1e6,
            top: -1e6,
            bottom: 0,
          };
          const titleInFlow = {
            left: (hr.left - fr.left) / scale,
            right: (hr.right - fr.left) / scale,
            top: (hr.top - fr.top) / scale,
            bottom: (hr.bottom - fr.top) / scale,
          };
          function segHits(p, q, b, pad) {
            const minX = Math.min(p.x, q.x), maxX = Math.max(p.x, q.x);
            const minY = Math.min(p.y, q.y), maxY = Math.max(p.y, q.y);
            const bl = b.left - pad, br = b.right + pad;
            const bt = b.top - pad, bb = b.bottom + pad;
            if (maxX < bl || minX > br || maxY < bt || minY > bb) return false;
            if (Math.abs(p.x - q.x) < 0.75) return p.x >= bl && p.x <= br;
            if (Math.abs(p.y - q.y) < 0.75) return p.y >= bt && p.y <= bb;
            return true;
          }
          const paths = {};
          const hitsTitle = [];
          const hitsOutside = [];
          const ends = [];
          const midYs = [];
          const finals = [];
          for (const src of sources) {
            const path = flow.querySelector(
              `svg.flow-svg path.flow-arrow[data-from="${src}"][data-to="${target}"]`
            );
            if (!path) continue;
            const pts = [];
            const re = /([ML])\\s*([-\\d.]+)\\s+([-\\d.]+)/g;
            let m;
            const d = path.getAttribute('d') || '';
            while ((m = re.exec(d))) pts.push({ x: +m[2], y: +m[3] });
            paths[src] = pts;
            for (let i = 1; i < pts.length; i++) {
              if (segHits(pts[i - 1], pts[i], titleInFlow, 0.5)) {
                hitsTitle.push(src);
              }
              // Any point above the flow content box (y < 0) is outside.
              if (pts[i - 1].y < -0.5 || pts[i].y < -0.5) hitsOutside.push(src);
              if (pts[i - 1].y > flow.clientHeight + 0.5 || pts[i].y > flow.clientHeight + 0.5) {
                hitsOutside.push(src);
              }
            }
            if (pts.length >= 4) {
              ends.push(pts[pts.length - 1].x);
              for (let i = 1; i < pts.length; i++) {
                if (
                  Math.abs(pts[i].y - pts[i - 1].y) < 0.75 &&
                  Math.abs(pts[i].x - pts[i - 1].x) >= 8
                ) {
                  midYs.push(pts[i].y);
                  finals.push(
                    Math.hypot(
                      pts[pts.length - 1].x - pts[pts.length - 2].x,
                      pts[pts.length - 1].y - pts[pts.length - 2].y
                    )
                  );
                  break;
                }
              }
            }
          }
          return {
            flowHeight: flow.clientHeight,
            padTop: parseFloat(getComputedStyle(flow).paddingTop) || 0,
            titleInFlow,
            hitsTitle: [...new Set(hitsTitle)],
            hitsOutside: [...new Set(hitsOutside)],
            ends,
            midYs,
            finals,
            paths,
          };
        }""",
        {
            "slideIndex": slide_index,
            "sources": sources,
            "target": target,
        },
    )


def test_same_row_fan_in_trunks_stay_inside_flow_and_miss_title(geometry_page):
    # Slide 40: four-source straight fan-in; slide 41: orthogonal twin.
    for slide_index, prefix in ((40, "17"), (41, "18")):
        sources = [f"p{prefix}", f"q{prefix}", f"r{prefix}", f"s{prefix}"]
        target = f"t{prefix}"
        meta = _detour_trunk_meta(geometry_page, slide_index, sources, target)
        assert not meta["hitsTitle"], (slide_index, meta)
        assert not meta["hitsOutside"], (slide_index, meta)
        assert len(meta["midYs"]) >= 3, (slide_index, meta)
        assert min(meta["midYs"]) >= 0, (slide_index, meta)
        # Nested trunks at distinct heights; outer still inside the grown box.
        assert max(meta["midYs"]) - min(meta["midYs"]) >= 30, (slide_index, meta)
        assert meta["padTop"] >= 50, (slide_index, meta)
        # Farther source keeps the farther (outer) port; no crossings.
        assert (
            meta["paths"][f"p{prefix}"][-1]["x"]
            > meta["paths"][f"r{prefix}"][-1]["x"]
        ), (slide_index, meta)


def test_same_row_detour_port_spacing_and_final_segment(geometry_page):
    meta = _detour_trunk_meta(
        geometry_page, 40, ["p17", "q17", "r17", "s17"], "t17"
    )
    ends = sorted(meta["ends"])
    assert len(ends) >= 3, meta
    gaps = [ends[i + 1] - ends[i] for i in range(len(ends) - 1)]
    assert min(gaps) >= 16, (gaps, meta)
    assert meta["finals"] and min(meta["finals"]) >= 18, meta


def test_same_row_fan_out_trunks_nested_not_collinear(geometry_page):
    # Slide 42: Source -> Alpha (direct), Beta, Gamma (detours).
    result = geometry_page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[42];
          const flow = slide.querySelector('.flow');
          function ptsOf(fromKey, toKey) {
            const path = flow.querySelector(
              `svg.flow-svg path.flow-arrow[data-from="${fromKey}"][data-to="${toKey}"]`
            );
            if (!path) return null;
            const pts = [];
            const re = /([ML])\\s*([-\\d.]+)\\s+([-\\d.]+)/g;
            let m;
            const d = path.getAttribute('d') || '';
            while ((m = re.exec(d))) pts.push({ x: +m[2], y: +m[3] });
            return pts;
          }
          function horizSegs(pts) {
            const segs = [];
            for (let i = 1; i < pts.length; i++) {
              if (
                Math.abs(pts[i].y - pts[i - 1].y) < 0.75 &&
                Math.abs(pts[i].x - pts[i - 1].x) >= 8
              ) {
                segs.push({
                  y: pts[i].y,
                  x0: Math.min(pts[i].x, pts[i - 1].x),
                  x1: Math.max(pts[i].x, pts[i - 1].x),
                });
              }
            }
            return segs;
          }
          function collinearOverlap(a, b) {
            if (Math.abs(a.y - b.y) > 0.75) return 0;
            const lo = Math.max(a.x0, b.x0);
            const hi = Math.min(a.x1, b.x1);
            return Math.max(0, hi - lo);
          }
          const beta = ptsOf('t19', 'y19');
          const gamma = ptsOf('t19', 'z19');
          if (!beta || !gamma) return { ok: false, reason: 'missing' };
          const hb = horizSegs(beta);
          const hg = horizSegs(gamma);
          let overlap = 0;
          for (const a of hb) {
            for (const b of hg) overlap = Math.max(overlap, collinearOverlap(a, b));
          }
          const midYs = [...hb, ...hg].map((s) => s.y);
          const starts = [beta[0].x, gamma[0].x];
          const finals = [
            Math.hypot(
              beta[beta.length - 1].x - beta[beta.length - 2].x,
              beta[beta.length - 1].y - beta[beta.length - 2].y
            ),
            Math.hypot(
              gamma[gamma.length - 1].x - gamma[gamma.length - 2].x,
              gamma[gamma.length - 1].y - gamma[gamma.length - 2].y
            ),
          ];
          return {
            ok: true,
            overlap,
            midYs,
            startGap: Math.abs(starts[0] - starts[1]),
            finals,
            beta,
            gamma,
          };
        }"""
    )
    assert result.get("ok"), result
    # Distinct nested trunks: no collinear overlap between different edges.
    assert result["overlap"] < 1, result
    assert max(result["midYs"]) - min(result["midYs"]) >= 16, result
    assert result["startGap"] >= 16, result
    assert min(result["finals"]) >= 18, result


def test_second_dashed_edge_does_not_cross_the_first(geometry_page):
    """A later dashed link can share a lane map without crossing the earlier one."""
    result = geometry_page.evaluate(
        r"""() => {
          const slide = Array.from(document.querySelectorAll('.slide')).find((s) =>
            (s.querySelector('h1') || {}).textContent.includes('Second dashed')
          );
          if (!slide) return { ok: false, reason: 'missing-slide' };
          const flow = slide.querySelector('.flow');
          function ptsOf(fromKey, toKey) {
            const path = flow.querySelector(
              `path.flow-arrow[data-from="${fromKey}"][data-to="${toKey}"]`
            );
            if (!path) return null;
            const pts = [];
            const re = /([ML])\s*([-\d.]+)\s+([-\d.]+)/g;
            let m;
            const d = path.getAttribute('d') || '';
            while ((m = re.exec(d))) pts.push({ x: parseFloat(m[2]), y: parseFloat(m[3]) });
            return pts;
          }
          function crosses(a, b) {
            const EPS = 0.75;
            function seg(a1, a2, b1, b2) {
              const aVert = Math.abs(a1.x - a2.x) < EPS;
              const bVert = Math.abs(b1.x - b2.x) < EPS;
              if (aVert === bVert) return false;
              const vert = aVert ? [a1, a2] : [b1, b2];
              const horz = aVert ? [b1, b2] : [a1, a2];
              const x = vert[0].x;
              const y = horz[0].y;
              const yLo = Math.min(vert[0].y, vert[1].y) + EPS;
              const yHi = Math.max(vert[0].y, vert[1].y) - EPS;
              const xLo = Math.min(horz[0].x, horz[1].x) + EPS;
              const xHi = Math.max(horz[0].x, horz[1].x) - EPS;
              return x > xLo && x < xHi && y > yLo && y < yHi;
            }
            let n = 0;
            for (let i = 1; i < a.length; i += 1) {
              for (let j = 1; j < b.length; j += 1) {
                if (seg(a[i - 1], a[i], b[j - 1], b[j])) n += 1;
              }
            }
            return n;
          }
          const back = ptsOf('l4', 'l2');
          const direct = ptsOf('u3', 'l3');
          if (!back || !direct) return { ok: false, reason: 'missing-path', back, direct };
          const n = crosses(back, direct);
          return { ok: n === 0, crossings: n, back, direct };
        }"""
    )
    assert result.get("ok"), result


def test_vertical_gap_label_is_accent_and_off_the_stroke(geometry_page):
    result = geometry_page.evaluate(
        r"""() => {
          const slide = Array.from(document.querySelectorAll('.slide')).find((s) =>
            (s.querySelector('h1') || {}).textContent.includes('Vertical gap')
          );
          if (!slide) return { ok: false, reason: 'missing-slide' };
          const flow = slide.querySelector('.flow');
          const path = flow.querySelector('path.flow-arrow-dashed');
          const label = flow.querySelector('text.flow-label-gap');
          if (!path || !label) return { ok: false, reason: 'missing', path: Boolean(path), label: Boolean(label) };
          const pb = path.getBBox();
          const lb = label.getBBox();
          const weight = getComputedStyle(label).fontWeight;
          const gap = getComputedStyle(flow).getPropertyValue('--color-edge-gap').trim();
          const muted = getComputedStyle(flow).getPropertyValue('--color-muted').trim();
          const fill = getComputedStyle(label).fill;
          const vertical = label.classList.contains('flow-label-gap-vertical');
          const overlapsX = lb.x < pb.x + pb.width && lb.x + lb.width > pb.x;
          const overlapsY = lb.y < pb.y + pb.height && lb.y + lb.height > pb.y;
          return {
            ok: vertical && lb.height > lb.width && !(overlapsX && overlapsY),
            vertical,
            tall: lb.height > lb.width,
            overlaps: overlapsX && overlapsY,
            weight,
            gap,
            muted,
            fill,
          };
        }"""
    )
    assert result.get("ok"), result
    assert result["weight"] in {"700", "bold"}, result
    assert result["gap"].lower() != result["muted"].lower()


def test_corner_index_sits_outside_the_title(geometry_page):
    result = geometry_page.evaluate(
        r"""() => {
          const slide = Array.from(document.querySelectorAll('.slide')).find((s) =>
            (s.querySelector('h1') || {}).textContent.includes('Corner index')
          );
          if (!slide) return { ok: false, reason: 'missing-slide' };
          const node = slide.querySelector('.flow-node[data-node="in"]');
          const badge = node.querySelector('.flow-node-index');
          const title = node.querySelector('.flow-node-title');
          const br = badge.getBoundingClientRect();
          const tr = title.getBoundingClientRect();
          return {
            ok: title.textContent.trim() === 'Intake'
              && !title.textContent.includes('①')
              && (br.right <= tr.left + 6 || br.bottom <= tr.top + 6),
            title: title.textContent,
            badge: badge.textContent,
            br: { left: br.left, top: br.top, right: br.right, bottom: br.bottom },
            tr: { left: tr.left, top: tr.top },
          };
        }"""
    )
    assert result.get("ok"), result


def test_ordinary_dash_is_arrow_colour_and_gap_is_opt_in(geometry_page):
    result = geometry_page.evaluate(
        r"""() => {
          const slide = Array.from(document.querySelectorAll('.slide')).find((s) =>
            (s.querySelector('h1') || {}).textContent.includes('Dashed stroke versus gap')
          );
          if (!slide) return { ok: false, reason: 'missing-slide' };
          const flow = slide.querySelector('.flow');
          const strokePx = parseFloat(getComputedStyle(flow).getPropertyValue('--flow-stroke-width'));
          const ordinary = flow.querySelector('path.flow-arrow[data-from="ord"]');
          const held = flow.querySelector('path.flow-arrow[data-from="gp"]');
          if (!ordinary || !held) return { ok: false, reason: 'missing-path' };
          const os = getComputedStyle(ordinary);
          const hs = getComputedStyle(held);
          const gapLabel = flow.querySelector('text.flow-label-gap');
          return {
            strokePx,
            ordinaryClass: ordinary.className.baseVal || ordinary.getAttribute('class'),
            heldClass: held.className.baseVal || held.getAttribute('class'),
            ordinaryMarker: ordinary.getAttribute('marker-end'),
            heldMarker: held.getAttribute('marker-end'),
            ordinaryStroke: os.stroke,
            heldStroke: hs.stroke,
            ordinaryWidth: parseFloat(os.strokeWidth),
            heldWidth: parseFloat(hs.strokeWidth),
            gapLabel: Boolean(gapLabel),
            ordinaryEmphasis: ordinary.getAttribute('data-emphasis'),
            heldEmphasis: held.getAttribute('data-emphasis'),
          };
        }"""
    )
    assert "flow-arrow-dashed" in result["ordinaryClass"], result
    assert "flow-arrow-gap" not in result["ordinaryClass"], result
    assert "flow-arrow-gap" in result["heldClass"], result
    assert "flow-arrowhead-gap" not in result["ordinaryMarker"], result
    assert "flow-arrowhead-gap" in result["heldMarker"], result
    assert result["ordinaryStroke"] != result["heldStroke"], result
    assert result["heldWidth"] >= result["ordinaryWidth"], result
    assert result["ordinaryWidth"] >= 3, result
    assert result["gapLabel"] is True
    assert result["ordinaryEmphasis"] in {None, ""}
    assert result["heldEmphasis"] == "gap"
    assert result["strokePx"] >= 3


def test_dashed_column_outline_is_darker_than_a_hairline(geometry_page):
    result = geometry_page.evaluate(
        r"""() => {
          const slide = Array.from(document.querySelectorAll('.slide')).find((s) =>
            (s.querySelector('h1') || {}).textContent.includes('Dashed card outline')
          );
          if (!slide) return { ok: false, reason: 'missing-slide' };
          const dashed = slide.querySelector('.column.dashed');
          const solid = Array.from(slide.querySelectorAll('.column')).find(
            (el) => !el.classList.contains('dashed')
          );
          if (!dashed || !solid) return { ok: false, reason: 'missing-column' };
          const d = getComputedStyle(dashed);
          const s = getComputedStyle(solid);
          return {
            style: d.borderTopStyle,
            width: parseFloat(d.borderTopWidth),
            color: d.borderTopColor,
            solidWidth: parseFloat(s.borderTopWidth),
            solidColor: s.borderTopColor,
          };
        }"""
    )
    assert result["style"] == "dashed", result
    assert result["width"] >= 2, result
    assert result["color"] in {"rgb(51, 51, 51)", "#333333"}, result
    assert result["color"] != result["solidColor"], result
