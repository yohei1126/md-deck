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
      return { gap: stack.left - start.right, targets };
    }"""
    result = page.evaluate(script)
    assert result["gap"] >= 64, result
    for target in result["targets"]:
        assert target["dy"] < 1, target
        assert target["run"] >= 18, target
        assert target["endDy"] <= 6, target
        assert target["endDx"] <= 2, target

    crushed_result = crushed.evaluate(script)
    assert crushed_result["gap"] >= 64, crushed_result
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
            groupRatio: group / slide.getBoundingClientRect().width,
            indexes: nodes.map((n) => n.index),
            stepClass: flow.classList.contains('flow-steps'),
          };
        }"""
    )
    assert abs(result["gaps"][0] - result["gaps"][1]) < 8, result
    assert 60 <= result["gaps"][0] <= 140, result
    assert abs(result["mid"] - result["flowW"] / 2) < 40, result
    assert result["inset"] > 80, result
    for width in result["widths"]:
        assert 200 <= width <= 260, result
    for height in result["heights"]:
        assert height >= 140, result
    assert 0.55 <= result["groupRatio"] <= 0.8, result
    assert result["stepClass"] is True, result
    assert result["indexes"] == ["counter(flow-step)"] * 3, result
