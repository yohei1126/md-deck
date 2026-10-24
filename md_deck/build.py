"""CLI: Markdown slides + style Markdown -> deterministic 16:9 PDF."""

from __future__ import annotations

import argparse
import hashlib
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from md_deck.slides import parse_deck
from md_deck.style import load_style_file, resolve_style_path, tokens_to_css

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = PACKAGE_DIR / "template"

# Fixed timestamp so identical sources yield identical PDF bytes.
PDF_DATE = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _read_template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def build_html(
    slides_html: list[str],
    theme_css: str,
    extra_css_files: list[Path],
    title: str,
) -> str:
    base_css = _read_template("base.css")
    deck_js = _read_template("deck.js")
    extras = []
    for path in extra_css_files:
        extras.append(path.read_text(encoding="utf-8"))
    extra_block = "\n".join(extras)

    slide_blocks = []
    for index, body in enumerate(slides_html, start=1):
        slide_blocks.append(
            f'<section class="slide" id="slide-{index}" data-slide="{index}">'
            f'<div class="slide-inner"><div class="slide-content">{body}</div></div>'
            f"</section>"
        )

    return f"""<!DOCTYPE html>
<html lang="ja">
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
            "Install requirements.txt."
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
    meta, slides = parse_deck(text)
    style_path = resolve_style_path(style, meta, source)
    tokens, style_extra = load_style_file(style_path)
    theme_css = tokens_to_css(tokens, style_extra)

    title = str(meta.get("title") or source.stem)
    html = build_html(slides, theme_css, extra_css or [], title)
    if keep_html is not None:
        keep_html.parent.mkdir(parents=True, exist_ok=True)
        keep_html.write_text(html, encoding="utf-8")

    return render_pdf(html, output, png_dir)


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="md_deck",
        description=(
            "Build a 16:9 PDF slide deck from Markdown. "
            "Visual style comes from a style Markdown file in the deck repo; "
            "md-deck ships layout mechanics only."
        ),
    )
    parser.add_argument("source", type=Path, help="Slides Markdown file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output PDF path",
    )
    parser.add_argument(
        "--style",
        type=Path,
        default=None,
        help="Style Markdown (YAML tokens + optional css fence). "
        "Required unless the slides front matter sets style:",
    )
    parser.add_argument(
        "--css",
        type=Path,
        action="append",
        default=[],
        help="Optional extra CSS file (repeatable). Applied after the style file.",
    )
    parser.add_argument(
        "--png",
        type=Path,
        default=None,
        metavar="DIR",
        help="Write one PNG per slide into DIR",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Also write the intermediate HTML to this path",
    )
    parser.add_argument(
        "--check-deterministic",
        action="store_true",
        help="Build twice and exit non-zero if PDF bytes differ",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not args.source.is_file():
        parser.error(f"Source not found: {args.source}")

    build_deck(
        source=args.source,
        output=args.output,
        style=args.style,
        extra_css=args.css,
        png_dir=args.png,
        keep_html=args.html,
    )

    if args.check_deterministic:
        with tempfile.TemporaryDirectory(prefix="md-deck-check-") as tmp:
            other = Path(tmp) / "second.pdf"
            build_deck(
                source=args.source,
                output=other,
                style=args.style,
                extra_css=args.css,
            )
            a = _file_digest(args.output)
            b = _file_digest(other)
            if a != b:
                raise SystemExit(
                    "Non-deterministic PDF output: SHA-256 differs between builds.\n"
                    f"  first:  {a}\n"
                    f"  second: {b}"
                )
            print(f"Deterministic OK (sha256={a})")
    else:
        print(f"Wrote {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
