"""md-deck CLI: `check` and `build` subcommands."""

from __future__ import annotations

import argparse
import hashlib
import tempfile
from pathlib import Path

from md_deck.build import build_deck
from md_deck.validate import check_deck, format_errors


def _add_style_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--style",
        type=Path,
        default=None,
        help="Style Markdown path (overrides slides front matter style:)",
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="md-deck",
        description=(
            "Build or check a 16:9 PDF slide deck from Markdown. "
            "Visual style comes from a style Markdown file in the deck repo."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    check_p = sub.add_parser(
        "check",
        help="Validate slides and style (no Chromium; report file:line errors)",
    )
    check_p.add_argument("source", type=Path, help="Slides Markdown file")
    _add_style_arg(check_p)
    check_p.add_argument(
        "--allow-html",
        action="store_true",
        help="Allow raw HTML in slides (forbidden by default)",
    )

    build_p = sub.add_parser(
        "build",
        help="Validate then render PDF via headless Chromium",
    )
    build_p.add_argument("source", type=Path, help="Slides Markdown file")
    build_p.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output PDF path",
    )
    _add_style_arg(build_p)
    build_p.add_argument(
        "--css",
        type=Path,
        action="append",
        default=[],
        help="Optional extra CSS file (repeatable)",
    )
    build_p.add_argument(
        "--png",
        type=Path,
        default=None,
        metavar="DIR",
        help="Write one PNG per slide into DIR",
    )
    build_p.add_argument(
        "--html",
        type=Path,
        default=None,
        help="Also write the intermediate HTML to this path",
    )
    build_p.add_argument(
        "--check-deterministic",
        action="store_true",
        help="Build twice and exit non-zero if PDF bytes differ",
    )
    build_p.add_argument(
        "--allow-html",
        action="store_true",
        help="Allow raw HTML in slides (forbidden by default)",
    )
    return parser


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _split_check(errors: list) -> tuple[list, list]:
    hard = [e for e in errors if not e.warning]
    warn = [e for e in errors if e.warning]
    return hard, warn


def _print_check(errors: list) -> tuple[list, list]:
    hard, warn = _split_check(errors)
    if errors:
        print(format_errors(errors))
    if hard and warn:
        print(f"{len(hard)} error(s), {len(warn)} warning(s)", flush=True)
    elif hard:
        print(f"{len(hard)} error(s)", flush=True)
    elif warn:
        print(f"{len(warn)} warning(s)", flush=True)
    return hard, warn


def _run_check(source: Path, style: Path | None, allow_html: bool) -> int:
    errors = check_deck(source, style, allow_html=allow_html)
    hard, _warn = _print_check(errors)
    if hard:
        return 1
    print(f"OK: {source}")
    return 0


def _run_build(args: argparse.Namespace) -> int:
    errors = check_deck(args.source, args.style, allow_html=args.allow_html)
    hard, _warn = _print_check(errors)
    if hard:
        print("refusing to build", flush=True)
        return 1

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
                print(
                    "Non-deterministic PDF output: SHA-256 differs between builds.\n"
                    f"  first:  {a}\n"
                    f"  second: {b}"
                )
                return 1
            print(f"Deterministic OK (sha256={a})")
    else:
        print(f"Wrote {args.output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not args.source.is_file():
        parser.error(f"Source not found: {args.source}")

    if args.command == "check":
        return _run_check(args.source, args.style, args.allow_html)
    if args.command == "build":
        return _run_build(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
