"""Rendered layout: fork gap, centred steps, cover title slide."""

from __future__ import annotations

from pathlib import Path

import pytest

from md_deck.build import build_html
from md_deck.slides import parse_deck
from md_deck.style import load_style_file, tokens_to_css

SLIDES = """---
title: Layout
subtitle: Quiet line
version: "1"
date: "2026-10-25"
lang: en
style: deck_style.md
---

# 骨子を先に見せる\\n色は抑えて残す

One centred line under the title.

---

# Branch

::: flow
Start {#start}
{ Keep / Change }
{#start} -> Keep
{#start} -> Change
:::

---

# Steps

::: flow wide steps
Collect -> Decide -> Record
:::

---

# Pinned

::: flow wide
Left -> Right
:::

::: question
Pinned line
:::

---

# Cards

::: columns panel
## One

- Alpha
- Beta
- Gamma

+++

## Two

- Alpha
- Beta
- Gamma
:::

---

# Map

::: flow
lane: Upper
A -> B
lane: Lower
C -> D
:::

---

# Map spread

::: flow spread
lane: Upper
A -> B
lane: Lower
C -> D
:::

---

# Copy

::: columns
## Short head

One sentence under the heading.

+++

## Other head

Second sentence.
:::

---

# Point

**Key Message:** **Ship** the draft

---

# Figures

::: columns figures
## 12

One line

+++

## 4

One line
:::

---

# Spread align

::: flow spread
lane: Intake
Alpha {#a1} -> Bravo {#a2} -> Charlie {#a3} -> Delta {#a4} -> Echo {#a5} -> Foxtrot {#a6}
lane: Partner
One {#b1} -> Two {#b2} -> Three {#b3} -> Four {#b4} -> Five {#b5} -> Six {#b6}
lane: [align=end]
Evidence {#ev}
link: ev ..> b6 : does not arrive [route=up]
link: a6 ..> ev : notice only on the edge [route=down]
:::

---

# Between labels

::: flow
lane:
Alpha {#a} -> Bravo {#b} -> Charlie {#c}
lane: [align=end]
Delta {#d}
link: a => d : solid note [route=between]
link: b ..> d : dashed note across [route=between]
:::

---

# Between spread

::: flow spread
lane:
Echo {#e} -> Foxtrot {#f} -> Golf {#g}
lane: [align=end]
Hotel {#h}
link: e => h : solid note [route=between]
link: f ..> h : dashed note across [route=between]
:::

---

# Short labels

::: flow
One {#o} -.[no match].-> Two {#t} -[red copy]-> Three {#r}
:::
"""

STYLE = """---
color_background: "#ffffff"
color_text: "#000000"
color_title: "#000000"
font_family: sans-serif
font_size_body: 22
font_size_title: 36
page_width: 1280
page_height: 720
page_padding: 48
---
"""

CRUSH = """
.flow-row { justify-content: space-between !important; gap: 0 !important; column-gap: 0 !important; }
.flow-node, .flow-stack { flex: 1 1 auto !important; }
.flow { flex: 1 1 auto; }
.slide-content > * { flex: 1 1 auto; }
"""


def _html(tmp: Path, extra_css: str = "") -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    slides = tmp / "slides.md"
    style = tmp / "deck_style.md"
    slides.write_text(SLIDES, encoding="utf-8")
    style.write_text(STYLE, encoding="utf-8")
    tokens, extra = load_style_file(style)
    meta, rendered = parse_deck(slides.read_text(encoding="utf-8"), style_tokens=tokens)
    css_files = []
    if extra_css:
        css_path = tmp / "extra.css"
        css_path.write_text(extra_css, encoding="utf-8")
        css_files.append(css_path)
    html = build_html(
        rendered,
        tokens_to_css(tokens, extra),
        css_files,
        str(meta.get("title") or "Layout"),
        subtitle=str(meta.get("subtitle") or ""),
        date=str(meta.get("date") or ""),
    )
    path = tmp / "deck.html"
    path.write_text(html, encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def layout_pages(tmp_path_factory):
    from playwright.sync_api import sync_playwright

    root = tmp_path_factory.mktemp("layout")
    plain = _html(root / "plain")
    crushed = _html(root / "crushed", CRUSH)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        page.goto(plain.resolve().as_uri(), wait_until="networkidle")
        page.wait_for_function("() => window.__mdDeckReady === true")
        other = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        other.goto(crushed.resolve().as_uri(), wait_until="networkidle")
        other.wait_for_function("() => window.__mdDeckReady === true")
        yield page, other
        browser.close()


def test_cover_is_a_centred_title_slide(layout_pages):
    page, _crushed = layout_pages
    result = page.evaluate(
        """() => {
          const slide = document.querySelector('.slide[data-cover="true"]');
          const title = slide.querySelector('h1.title');
          const meta = slide.querySelector('.cover-meta');
          const sr = slide.getBoundingClientRect();
          const tr = title.getBoundingClientRect();
          return {
            meta: meta ? meta.textContent : '',
            titleTop: tr.top - sr.top,
            titleCx: (tr.left + tr.right) / 2,
            slideCx: (sr.left + sr.right) / 2,
          };
        }"""
    )
    assert "Quiet line" in result["meta"]
    assert "2026-10-25" in result["meta"]
    assert result["titleTop"] > 160, result
    assert abs(result["titleCx"] - result["slideCx"]) < 24, result


def test_branch_fork_has_gap_and_arrowheads(layout_pages):
    page, crushed = layout_pages
    script = """() => {
      const slide = document.querySelectorAll('.slide')[1];
      const flow = slide.querySelector('.flow');
      const scale = Number(slide.dataset.scale || '1') || 1;
      const flowRect = flow.getBoundingClientRect();
      function box(el) {
        const r = el.getBoundingClientRect();
        return {
          left: (r.left - flowRect.left) / scale,
          right: (r.right - flowRect.left) / scale,
          cy: ((r.top + r.bottom) / 2 - flowRect.top) / scale,
        };
      }
      function ptsOf(key) {
        const path = flow.querySelector(`path.flow-arrow[data-to="${key}"]`);
        const pts = [];
        const re = /([ML])\\s*([-\\d.]+)\\s+([-\\d.]+)/g;
        let m;
        const d = path ? path.getAttribute('d') || '' : '';
        while ((m = re.exec(d))) pts.push({ x: +m[2], y: +m[3] });
        return pts;
      }
      const start = box(flow.querySelector('.flow-node[data-node="start"]'));
      const stack = box(flow.querySelector('.flow-stack'));
      const keepEl = flow.querySelector('.flow-node[data-node="Keep"]');
      const changeEl = flow.querySelector('.flow-node[data-node="Change"]');
      const kr = keepEl.getBoundingClientRect();
      const cr = changeEl.getBoundingClientRect();
      const upper = kr.top <= cr.top ? kr : cr;
      const lower = kr.top <= cr.top ? cr : kr;
      const stackGap = (lower.top - upper.bottom) / scale;
      const targets = ['Keep', 'Change'].map((key) => {
        const node = box(flow.querySelector(`.flow-node[data-node="${key}"]`));
        const pts = ptsOf(key);
        const last = pts[pts.length - 1];
        const prev = pts[pts.length - 2];
        return {
          key,
          run: Math.hypot(last.x - prev.x, last.y - prev.y),
          dy: Math.abs(last.y - prev.y),
          endDy: Math.abs(last.y - node.cy),
          endDx: Math.abs(last.x - node.left),
        };
      });
      const row = flow.querySelector('.flow-row');
      return {
        gap: stack.left - start.right,
        stackGap,
        targets,
        startW: start.right - start.left,
        stackW: stack.right - stack.left,
        flowH: flow.getBoundingClientRect().height / scale,
        rowH: row.getBoundingClientRect().height / scale,
      };
    }"""
    result = page.evaluate(script)
    assert result["gap"] >= 64, result
    assert 24 <= result["stackGap"] <= 48, result
    assert result["flowH"] - result["rowH"] < 80, result
    assert result["startW"] < 240, result
    assert result["stackW"] > result["startW"] * 2, result
    for target in result["targets"]:
        assert target["dy"] < 1, target
        assert target["run"] >= 18, target
        assert target["endDy"] <= 6, target
        assert target["endDx"] <= 2, target

    crushed_result = crushed.evaluate(script)
    assert crushed_result["gap"] >= 64, crushed_result
    assert crushed_result["flowH"] - crushed_result["rowH"] < 80, crushed_result
    for target in crushed_result["targets"]:
        assert target["run"] >= 18, target
        assert target["endDx"] <= 2, target


def test_wide_steps_are_centred_with_even_gaps(layout_pages):
    page, _crushed = layout_pages
    result = page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[2];
          const flow = slide.querySelector('.flow');
          const scale = Number(slide.dataset.scale || '1') || 1;
          const flowRect = flow.getBoundingClientRect();
          const nodes = ['Collect', 'Decide', 'Record'].map((key) => {
            const el = flow.querySelector(`.flow-node[data-node="${key}"]`);
            const r = el.getBoundingClientRect();
            const title = el.querySelector('.flow-node-title');
            return {
              left: (r.left - flowRect.left) / scale,
              right: (r.right - flowRect.left) / scale,
              width: r.width / scale,
              height: r.height / scale,
              index: getComputedStyle(title, '::before').content,
            };
          });
          const gaps = [
            nodes[1].left - nodes[0].right,
            nodes[2].left - nodes[1].right,
          ];
          const mid = (nodes[0].left + nodes[2].right) / 2;
          const group = nodes[2].right - nodes[0].left;
          return {
            gaps,
            mid,
            flowW: flow.clientWidth,
            inset: nodes[0].left,
            widths: nodes.map((n) => n.width),
            heights: nodes.map((n) => n.height),
            flowH: flow.getBoundingClientRect().height / scale,
            groupRatio: group / slide.getBoundingClientRect().width,
            indexes: nodes.map((n) => n.index),
            stepClass: flow.classList.contains('flow-steps'),
          };
        }"""
    )
    assert abs(result["gaps"][0] - result["gaps"][1]) < 8, result
    assert 60 <= result["gaps"][0] <= 140, result
    assert abs(result["mid"] - result["flowW"] / 2) < 40, result
    assert result["inset"] < 48, result
    for width in result["widths"]:
        assert width >= 280, result
    for height in result["heights"]:
        assert 220 <= height <= 460, result
    assert result["flowH"] - max(result["heights"]) < 80, result
    assert result["groupRatio"] >= 0.8, result
    assert result["stepClass"] is True, result
    assert result["indexes"] == ["counter(flow-step)"] * 3, result
    tops = page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[2];
          return Array.from(slide.querySelectorAll('.flow-node')).map((el) => {
            const box = el.getBoundingClientRect();
            const title = el.querySelector('.flow-node-title').getBoundingClientRect();
            return {
              titleFromTop: title.top - box.top,
              titleFromBottom: box.bottom - title.bottom,
              height: box.height,
            };
          });
        }"""
    )
    for node in tops:
        assert node["titleFromTop"] < 36, tops
        assert node["titleFromBottom"] > node["height"] * 0.4, tops
    place = page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[2];
          const content = slide.querySelector('.slide-content');
          const title = slide.querySelector('h1');
          const flow = slide.querySelector('.flow');
          const cr = content.getBoundingClientRect();
          const tr = title.getBoundingClientRect();
          const fr = flow.getBoundingClientRect();
          return {
            titleGap: tr.top - cr.top,
            above: fr.top - tr.bottom,
            below: cr.bottom - fr.bottom,
          };
        }"""
    )
    assert place["titleGap"] < 20, place
    assert place["above"] > 40, place
    assert place["below"] > 40, place
    assert abs(place["above"] - place["below"]) < 48, place


def test_question_stays_at_the_bottom_with_space_split(layout_pages):
    page, _crushed = layout_pages
    result = page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[3];
          const content = slide.querySelector('.slide-content');
          const title = slide.querySelector('h1');
          const flow = slide.querySelector('.flow');
          const question = slide.querySelector('.question');
          const cr = content.getBoundingClientRect();
          const tr = title.getBoundingClientRect();
          const fr = flow.getBoundingClientRect();
          const qr = question.getBoundingClientRect();
          return {
            titleGap: tr.top - cr.top,
            underHeading: fr.top - tr.bottom,
            between: qr.top - fr.bottom,
            under: cr.bottom - qr.bottom,
          };
        }"""
    )
    assert result["titleGap"] < 20, result
    assert result["under"] < 48, result
    assert result["underHeading"] > 24, result
    assert result["between"] > 24, result
    assert abs(result["underHeading"] - result["between"]) < 64, result


def test_column_list_stays_under_the_heading(layout_pages):
    page, _crushed = layout_pages
    result = page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[4];
          const content = slide.querySelector('.slide-content');
          const title = slide.querySelector('h1');
          const card = slide.querySelector('.column');
          const head = card.querySelector('.column-head');
          const items = Array.from(card.querySelectorAll('li'));
          const cr = content.getBoundingClientRect();
          const tr = title.getBoundingClientRect();
          const cardBox = card.getBoundingClientRect();
          const headBox = head.getBoundingClientRect();
          const first = items[0].getBoundingClientRect();
          const last = items[items.length - 1].getBoundingClientRect();
          return {
            titleGap: tr.top - cr.top,
            cardH: cardBox.height,
            headGap: first.top - headBox.bottom,
            itemGap: items[1].getBoundingClientRect().top - first.bottom,
            lastFromBottom: cardBox.bottom - last.bottom,
            lineHeight: parseFloat(getComputedStyle(items[0]).lineHeight),
            fontSize: parseFloat(getComputedStyle(items[0]).fontSize),
          };
        }"""
    )
    assert result["titleGap"] < 20, result
    assert result["cardH"] > 280, result
    assert result["headGap"] < 28, result
    assert result["itemGap"] < 36, result
    assert result["lastFromBottom"] > result["cardH"] * 0.35, result
    assert result["lineHeight"] < result["fontSize"] * 1.7, result


def test_spread_lane_map_spans_the_content_width(layout_pages):
    page, _crushed = layout_pages
    result = page.evaluate(
        """() => {
          const slides = document.querySelectorAll('.slide');
          function measure(slide) {
            const content = slide.querySelector('.slide-content');
            const lanes = slide.querySelector('.flow-lanes');
            const node = slide.querySelector('.flow-node');
            const cr = content.getBoundingClientRect();
            const lr = lanes.getBoundingClientRect();
            const nr = node.getBoundingClientRect();
            return {
              lanesW: lr.width,
              contentW: cr.width,
              nodeW: nr.width,
              nodeH: nr.height,
              mid: (lr.left + lr.right) / 2 - cr.left,
            };
          }
          return { plain: measure(slides[5]), spread: measure(slides[6]) };
        }"""
    )
    plain, spread = result["plain"], result["spread"]
    assert plain["lanesW"] < plain["contentW"] * 0.55, result
    assert abs(plain["mid"] - plain["contentW"] / 2) < 40, result
    assert spread["lanesW"] > spread["contentW"] * 0.85, result
    assert spread["nodeW"] > plain["nodeW"] * 1.5, result
    assert spread["nodeH"] < 200, result


def test_card_paragraph_sits_under_the_heading(layout_pages):
    page, _crushed = layout_pages
    result = page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[7];
          const card = slide.querySelector('.column');
          const head = card.querySelector('.column-head');
          const para = card.querySelector('p');
          const cardBox = card.getBoundingClientRect();
          const hr = head.getBoundingClientRect();
          const pr = para.getBoundingClientRect();
          return {
            cardH: cardBox.height,
            gap: pr.top - hr.bottom,
            headPx: parseFloat(getComputedStyle(head).fontSize),
            bodyPx: parseFloat(getComputedStyle(card).fontSize),
          };
        }"""
    )
    assert result["cardH"] > 280, result
    assert result["gap"] < 24, result
    assert abs(result["headPx"] - result["bodyPx"] * 1.1) < 2, result


def test_key_message_and_figure_are_bold_and_large(layout_pages):
    page, _crushed = layout_pages
    result = page.evaluate(
        """() => {
          const point = document.querySelectorAll('.slide')[8];
          const figures = document.querySelectorAll('.slide')[9];
          const message = point.querySelector('.key-message');
          const head = figures.querySelector('.column-head');
          return {
            weight: getComputedStyle(message).fontWeight,
            strong: message.querySelector('strong') !== null,
            figurePx: parseFloat(getComputedStyle(head).fontSize),
            bodyPx: parseFloat(getComputedStyle(figures).fontSize),
          };
        }"""
    )
    assert result["weight"] in {"700", "bold"}, result
    assert result["strong"] is True, result
    assert abs(result["figurePx"] - result["bodyPx"] * 2.4) < 2, result
    place = page.evaluate(
        """() => {
          const figures = document.querySelectorAll('.slide')[9];
          const card = figures.querySelector('.column');
          const head = card.querySelector('.column-head');
          const para = card.querySelector('p');
          const cardBox = card.getBoundingClientRect();
          const hr = head.getBoundingClientRect();
          const pr = para.getBoundingClientRect();
          return {
            cardH: cardBox.height,
            groupMid: (hr.top + pr.bottom) / 2,
            cardMid: (cardBox.top + cardBox.bottom) / 2,
            align: getComputedStyle(card).textAlign,
          };
        }"""
    )
    assert abs(place["groupMid"] - place["cardMid"]) < 36, place
    assert place["align"] == "center", place


def test_spread_with_align_end_keeps_nodes_and_labels_inside(layout_pages):
    page, _crushed = layout_pages
    result = page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[10];
          const sr = slide.getBoundingClientRect();
          const content = slide.querySelector('.slide-content').getBoundingClientRect();
          const lanes = slide.querySelector('.flow-lanes').getBoundingClientRect();
          const nodes = Array.from(slide.querySelectorAll('.flow-node')).map((el) => {
            const r = el.getBoundingClientRect();
            return {
              id: el.dataset.node,
              left: r.left,
              right: r.right,
              top: r.top,
              bottom: r.bottom,
              width: r.width,
            };
          });
          const labels = Array.from(slide.querySelectorAll('text.flow-label')).map((el) => {
            const r = el.getBoundingClientRect();
            return {
              text: el.textContent,
              left: r.left,
              right: r.right,
              top: r.top,
              bottom: r.bottom,
            };
          });
          function hits(label) {
            return nodes.some((node) => {
              const w = Math.min(label.right, node.right) - Math.max(label.left, node.left);
              const h = Math.min(label.bottom, node.bottom) - Math.max(label.top, node.top);
              return w > 2 && h > 2;
            });
          }
          const byId = Object.fromEntries(nodes.map((node) => [node.id, node]));
          return {
            contentRight: content.right,
            contentLeft: content.left,
            slideRight: sr.right,
            slideLeft: sr.left,
            lanesW: lanes.width,
            contentW: content.width,
            nodes: nodes.map((node) => ({
              id: node.id,
              pastContent: node.right - content.right,
              beforeContent: content.left - node.left,
              width: node.width,
            })),
            labels: labels.map((label) => ({
              text: label.text,
              pastSlide: label.right - sr.right,
              beforeSlide: sr.left - label.left,
              hitsNode: hits(label),
            })),
            endAlign: byId.ev && byId.b6
              ? { evRight: byId.ev.right, b6Right: byId.b6.right, evLeft: byId.ev.left, b6Left: byId.b6.left }
              : null,
          };
        }"""
    )
    assert result["lanesW"] > result["contentW"] * 0.85, result
    assert result["endAlign"] is not None, result
    assert abs(result["endAlign"]["evRight"] - result["endAlign"]["b6Right"]) < 8, result
    assert result["endAlign"]["evLeft"] > result["endAlign"]["b6Left"] + 20, result
    for node in result["nodes"]:
        assert node["pastContent"] <= 1, node
        assert node["beforeContent"] <= 1, node
    assert len(result["labels"]) >= 2, result
    for label in result["labels"]:
        assert label["pastSlide"] <= -4, label
        assert label["beforeSlide"] <= -4, label
        assert label["hitsNode"] is False, label


def test_between_route_labels_clear_horizontal_strokes(layout_pages):
    """route=between labels sit above or below the gap shaft, not on it.

    Two links share the lane gap (the parties shape). Each label must clear
    its own horizontal shaft, the other link's shaft, and the arrowhead.
    """
    page, _crushed = layout_pages
    result = page.evaluate(
        """() => {
          function pointsOf(d) {
            const pts = [];
            const re = /([ML])\\s*([-\\d.]+)\\s+([-\\d.]+)/g;
            let m;
            while ((m = re.exec(d))) pts.push({ x: +m[2], y: +m[3] });
            return pts;
          }
          function longestHorizontal(pts) {
            let best = null;
            for (let i = 1; i < pts.length; i += 1) {
              const p = pts[i - 1];
              const q = pts[i];
              const dx = Math.abs(q.x - p.x);
              const dy = Math.abs(q.y - p.y);
              if (dy > 0.75 || dx < 8) continue;
              if (!best || dx > best.len) {
                best = {
                  y: (p.y + q.y) / 2,
                  len: dx,
                  x0: Math.min(p.x, q.x),
                  x1: Math.max(p.x, q.x),
                };
              }
            }
            return best;
          }
          function hitsSegment(box, seg, pad) {
            if (seg.y < box.top - pad || seg.y > box.bottom + pad) return false;
            return seg.x1 >= box.left - pad && seg.x0 <= box.right + pad;
          }
          function hitsArrowhead(box, pts) {
            if (pts.length < 2) return false;
            const end = pts[pts.length - 1];
            const prev = pts[pts.length - 2];
            const dx = end.x - prev.x;
            const dy = end.y - prev.y;
            const len = Math.hypot(dx, dy) || 1;
            const back = Math.min(18, len);
            const hx = end.x - (dx / len) * back;
            const hy = end.y - (dy / len) * back;
            const half = 7;
            const head = {
              left: Math.min(end.x, hx) - half,
              right: Math.max(end.x, hx) + half,
              top: Math.min(end.y, hy) - half,
              bottom: Math.max(end.y, hy) + half,
            };
            const w = Math.min(box.right, head.right) - Math.max(box.left, head.left);
            const h = Math.min(box.bottom, head.bottom) - Math.max(box.top, head.top);
            return w > 1 && h > 1;
          }
          return [11, 12].map((index) => {
            const slide = document.querySelectorAll('.slide')[index];
            const sr = slide.getBoundingClientRect();
            const flow = slide.querySelector('.flow');
            const labels = Array.from(flow.querySelectorAll('text.flow-edge-label'));
            const rows = labels.map((label) => {
              const lb = label.getBBox();
              const box = {
                left: lb.x,
                right: lb.x + lb.width,
                top: lb.y,
                bottom: lb.y + lb.height,
              };
              const path = flow.querySelector(
                `path.flow-arrow[data-from="${label.dataset.from}"][data-to="${label.dataset.to}"]`
              );
              const pts = path ? pointsOf(path.getAttribute('d')) : [];
              const shaft = longestHorizontal(pts);
              const r = label.getBoundingClientRect();
              return {
                text: label.textContent,
                from: label.dataset.from,
                to: label.dataset.to,
                box,
                shaft,
                above: shaft ? box.bottom <= shaft.y - 4 : false,
                below: shaft ? box.top >= shaft.y + 4 : false,
                pastSlide: r.right - sr.right,
                beforeSlide: sr.left - r.left,
                arrow: hitsArrowhead(box, pts),
              };
            });
            rows.forEach((row) => {
              row.crossesOther = rows.some((other) => {
                if (other === row || !other.shaft) return false;
                return hitsSegment(row.box, other.shaft, 2);
              });
            });
            return {
              index,
              spread: flow.classList.contains('flow-spread'),
              rows,
            };
          });
        }"""
    )
    assert len(result) == 2, result
    assert result[0]["spread"] is False, result[0]
    assert result[1]["spread"] is True, result[1]
    for slide in result:
        assert len(slide["rows"]) == 2, slide
        for row in slide["rows"]:
            assert row["shaft"] is not None, row
            assert row["shaft"]["len"] > 80, row
            assert row["above"] or row["below"], row
            assert row["crossesOther"] is False, row
            overlap = min(row["box"]["right"], row["shaft"]["x1"]) - max(
                row["box"]["left"], row["shaft"]["x0"]
            )
            assert overlap > 24, row
            assert row["pastSlide"] <= -4, row
            assert row["beforeSlide"] <= -4, row
            assert row["arrow"] is False, row
        boxes = [row["box"] for row in slide["rows"]]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1 :]:
                w = min(a["right"], b["right"]) - max(a["left"], b["left"])
                h = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
                assert w <= 2 or h <= 2, slide


def test_short_horizontal_labels_stay_clear_of_endpoint_boxes(layout_pages):
    """Same-row labels stay at mid-shaft, outside both endpoint boxes.

    A short chain (the route-map / parties row) must not slide the label
    onto the source box to dodge the arrowhead.
    """
    page, _crushed = layout_pages
    result = page.evaluate(
        """() => {
          const slide = document.querySelectorAll('.slide')[13];
          const flow = slide.querySelector('.flow');
          const origin = flow.getBoundingClientRect();
          const scale = Number(slide.dataset.scale || '1') || 1;
          function rel(el) {
            const r = el.getBoundingClientRect();
            return {
              left: (r.left - origin.left) / scale,
              right: (r.right - origin.left) / scale,
              top: (r.top - origin.top) / scale,
              bottom: (r.bottom - origin.top) / scale,
            };
          }
          function pointsOf(d) {
            const pts = [];
            const re = /([ML])\\s*([-\\d.]+)\\s+([-\\d.]+)/g;
            let m;
            while ((m = re.exec(d))) pts.push({ x: +m[2], y: +m[3] });
            return pts;
          }
          function hits(a, b) {
            const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
            const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
            return w > 0.5 && h > 0.5;
          }
          return Array.from(flow.querySelectorAll('text.flow-edge-label')).map((label) => {
            const lb = label.getBBox();
            const box = {
              left: lb.x,
              right: lb.x + lb.width,
              top: lb.y,
              bottom: lb.y + lb.height,
              cx: lb.x + lb.width / 2,
            };
            const path = flow.querySelector(
              `path.flow-arrow[data-from="${label.dataset.from}"][data-to="${label.dataset.to}"]`
            );
            const pts = pointsOf(path.getAttribute('d'));
            let shaft = null;
            for (let i = 1; i < pts.length; i += 1) {
              const dx = Math.abs(pts[i].x - pts[i - 1].x);
              const dy = Math.abs(pts[i].y - pts[i - 1].y);
              if (dy > 0.75 || dx < 8) continue;
              if (!shaft || dx > shaft.len) {
                shaft = {
                  y: (pts[i - 1].y + pts[i].y) / 2,
                  len: dx,
                  mid: (pts[i - 1].x + pts[i].x) / 2,
                };
              }
            }
            const src = rel(flow.querySelector(`.flow-node[data-node="${label.dataset.from}"]`));
            const dst = rel(flow.querySelector(`.flow-node[data-node="${label.dataset.to}"]`));
            return {
              text: label.textContent,
              box,
              shaft,
              hitsSrc: hits(box, src),
              hitsDst: hits(box, dst),
              above: shaft ? box.bottom <= shaft.y - 4 : false,
              below: shaft ? box.top >= shaft.y + 4 : false,
              offCenter: shaft ? Math.abs(box.cx - shaft.mid) : null,
            };
          });
        }"""
    )
    assert len(result) == 2, result
    for row in result:
        assert row["shaft"] is not None, row
        assert row["shaft"]["len"] < 160, row
        assert row["box"]["right"] - row["box"]["left"] > 40, row
        assert row["above"] or row["below"], row
        assert row["hitsSrc"] is False, row
        assert row["hitsDst"] is False, row
        assert row["offCenter"] < 8, row
