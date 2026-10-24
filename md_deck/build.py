"""Markdown slides + style Markdown -> deterministic 16:9 PDF."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from md_deck.slides import SlideRender, parse_deck
from md_deck.style import load_style_file, resolve_style_path, tokens_to_css

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = PACKAGE_DIR / "template"

# Fixed timestamp so identical sources yield identical PDF bytes.
PDF_DATE = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _read_template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def build_html(
    slides: list[SlideRender],
    theme_css: str,
    extra_css_files: list[Path],
    title: str,
    lang: str = "en",
) -> str:
    base_css = _read_template("base.css")
    deck_js = _read_template("deck.js")
    extras = []
    for path in extra_css_files:
        extras.append(path.read_text(encoding="utf-8"))
    extra_block = "\n".join(extras)

    total = len(slides)
    slide_blocks = []
    for index, slide in enumerate(slides, start=1):
        classes = ["slide"]
        if slide.slide_classes:
            classes.extend(slide.slide_classes)
        class_attr = " ".join(classes)
        # Prefer author id from heading attrs; else stable slide-N.
        slide_id = slide.slide_id or f"slide-{index}"
        source = ""
        if slide.source_html:
            source = f'<div class="source">{slide.source_html}</div>'
        footer = (
            f'<footer class="slide-footer">'
            f"{source}"
            f'<div class="page-number">{index} / {total}</div>'
            f"</footer>"
        )
        slide_blocks.append(
            f'<section class="{class_attr}" id="{_escape(slide_id)}" '
            f'data-index="{index}" data-slide="{index}">'
            f'<div class="slide-inner"><div class="slide-content">{slide.html}</div></div>'
            f"{footer}"
            f"</section>"
        )

    lang_attr = _escape(lang or "en")
    return f"""<!DOCTYPE html>
<html lang="{lang_attr}">
<head>
<meta charset="utf-8"/>
<title>{_escape(title)}</title>
<style>
{base_css}
</style>
<style>
{theme_css}
</style>
<style>
{extra_block}
</style>
</head>
<body>
<main class="deck">
{"".join(slide_blocks)}
</main>
<script>
{deck_js}
</script>
</body>
</html>
"""


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _pdf_date_string(dt: datetime) -> str:
    # PDF date format D:YYYYMMDDHHmmSSOHH'mm
    return "D:" + dt.strftime("%Y%m%d%H%M%S") + "+00'00'"


def _normalize_pdf(path: Path) -> None:
    """Rewrite PDF metadata to fixed values for byte-stable output."""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "pypdf is required for deterministic PDF metadata. "
            "Run `uv sync` in the md-deck checkout."
        ) from exc

    reader = PdfReader(str(path))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    date_str = _pdf_date_string(PDF_DATE)
    writer.add_metadata(
        {
            "/Producer": "md-deck",
            "/Creator": "md-deck",
            "/Title": reader.metadata.title if reader.metadata else "deck",
            "/CreationDate": date_str,
            "/ModDate": date_str,
        }
    )
    # Disable object IDs that vary across runs when possible.
    with path.open("wb") as fh:
        writer.write(fh)


def render_pdf(
    html: str,
    output: Path,
    png_dir: Path | None,
    fail_on_overflow: bool = True,
) -> list[int]:
    from playwright.sync_api import sync_playwright

    output.parent.mkdir(parents=True, exist_ok=True)
    if png_dir is not None:
        png_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="md-deck-") as tmp:
        html_path = Path(tmp) / "deck.html"
        html_path.write_text(html, encoding="utf-8")
        file_url = html_path.resolve().as_uri()

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": 1280, "height": 720},
                device_scale_factor=1,
            )
            page.goto(file_url, wait_until="networkidle")
            page.wait_for_function("() => window.__mdDeckReady === true")
            overflows = page.evaluate("() => window.__mdDeckOverflows || []")

            page.pdf(
                path=str(output),
                width="1280px",
                height="720px",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            )

            if png_dir is not None:
                slides = page.query_selector_all(".slide")
                for index, slide in enumerate(slides, start=1):
                    slide.screenshot(
                        path=str(png_dir / f"slide-{index:02d}.png"),
                        type="png",
                        animations="disabled",
                    )

            browser.close()

    _normalize_pdf(output)

    if overflows and fail_on_overflow:
        joined = ", ".join(str(n) for n in overflows)
        raise SystemExit(
            f"Slide overflow after shrinking to 80%: slide(s) {joined}. "
            "Shorten content or adjust the style tokens."
        )
    return list(overflows)


def build_deck(
    source: Path,
    output: Path,
    style: Path | None = None,
    extra_css: list[Path] | None = None,
    png_dir: Path | None = None,
    keep_html: Path | None = None,
) -> list[int]:
    text = source.read_text(encoding="utf-8")
    # Need style tokens before parse for label defaults override
    # Resolve style path needs meta first — peek front matter
    from md_deck.slides import split_front_matter

    meta_peek, _ = split_front_matter(text)
    style_path = resolve_style_path(style, meta_peek, source)
    tokens, style_extra = load_style_file(style_path)
    theme_css = tokens_to_css(tokens, style_extra)

    meta, slides = parse_deck(text, style_tokens=tokens)
    title = str(meta.get("title") or source.stem)
    lang = str(meta.get("lang") or "en")
    html = build_html(slides, theme_css, extra_css or [], title, lang=lang)
    if keep_html is not None:
        keep_html.parent.mkdir(parents=True, exist_ok=True)
        keep_html.write_text(html, encoding="utf-8")

    return render_pdf(html, output, png_dir)


# Console entry point lives in md_deck.cli (keeps this module Chromium-focused).
