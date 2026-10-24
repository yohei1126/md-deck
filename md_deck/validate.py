"""Pure-Python deck validation for `md-deck check` (no Chromium)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from md_deck.errors import CheckError, sort_errors
from md_deck.style import FRONT_MATTER_RE, TOKEN_SPEC

KNOWN_BLOCK_KINDS = frozenset({"question", "flow", "columns"})
SLIDES_OPTIONAL_KEYS = frozenset({"subtitle", "author", "audience"})
SLIDES_REQUIRED_KEYS = frozenset({"title", "version", "date", "lang", "style"})
SLIDES_ALLOWED_KEYS = SLIDES_REQUIRED_KEYS | SLIDES_OPTIONAL_KEYS

REQUIRED_STYLE_TOKENS = frozenset(
    {
        "color_background",
        "color_text",
        "color_title",
        "font_family",
        "font_size_body",
    }
)

COLOR_RE = re.compile(
    r"^(?:"
    r"#[0-9a-fA-F]{3}"
    r"|#[0-9a-fA-F]{6}"
    r"|#[0-9a-fA-F]{8}"
    r"|rgb\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*\)"
    r"|rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*\)"
    r"|hsl\(\s*[\d.]+\s*,\s*[\d.]+%\s*,\s*[\d.]+%\s*\)"
    r"|hsla\(\s*[\d.]+\s*,\s*[\d.]+%\s*,\s*[\d.]+%\s*,\s*[\d.]+\s*\)"
    r"|[a-zA-Z]{3,30}"
    r")$"
)
SIZE_STR_RE = re.compile(r"^[0-9]+(\.[0-9]+)?(px|rem|em|%)$")
KEY_MESSAGE_LINE_RE = re.compile(
    r"^\s*\*\*Key Message:\*\*\s*(?P<body>.*)$",
    re.IGNORECASE,
)
H1_RE = re.compile(r"^#\s+\S")
HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
FENCE_TICKS_RE = re.compile(r"^(`{3,}|~{3,})")
COLON_FENCE_RE = re.compile(r"^(:{2,})\s*(.*)$")

# pymarkdown rules useful for deck slide bodies (generic Markdown hygiene).
PYMARKDOWN_ENABLE = (
    "md001",  # heading increment
    "md005",  # list indent consistency
    "md007",  # ul indent
    "md010",  # hard tabs
    "md027",  # multiple spaces after blockquote
    "md030",  # list marker space
    "md031",  # fenced code blanks
    "md040",  # fenced code language
    "md046",  # code block style
)
PYMARKDOWN_DISABLE = (
    "md012",  # consecutive blanks — ::: scrubbing would false-positive
    "md013",  # line length
    "md022",  # blanks around headings (tight slides)
    "md024",  # duplicate headings across slides OK when scanned separately
    "md025",  # multiple H1 — we enforce ourselves
    "md026",  # trailing punctuation
    "md029",  # ordered list prefix
    "md032",  # blanks around lists (tight slides)
    "md033",  # raw HTML — we enforce with --allow-html
    "md034",  # bare URL
    "md036",  # emphasis as heading
    "md041",  # first line heading — slides may start after blank
    "md047",  # trailing newline
)


@dataclass
class SlideSlice:
    index: int  # 1-based
    start_line: int  # 1-based line of first content line
    text: str


def schemas_dir() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / "schemas",
        here / "schemas",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    raise FileNotFoundError("schemas/ directory not found next to the package")


def load_schema(name: str) -> dict[str, Any]:
    path = schemas_dir() / name
    return json.loads(path.read_text(encoding="utf-8"))


def _yaml_front_matter(text: str) -> tuple[Any | None, int, int, str, list[CheckError]]:
    """Return (loaded, fm_start_line, body_start_line, body, errors)."""
    errors: list[CheckError] = []
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return None, 1, 1, text, errors
    fm_text = match.group(1)
    fm_start = 2  # line after opening ---
    body = text[match.end() :]
    body_start = text[: match.end()].count("\n") + 1
    try:
        loaded = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        line = fm_start
        if hasattr(exc, "problem_mark") and exc.problem_mark is not None:
            line = fm_start + int(exc.problem_mark.line)
        errors.append(
            CheckError("", line, f"invalid YAML front matter: {exc}")
        )
        return None, fm_start, body_start, body, errors
    return loaded, fm_start, body_start, body, errors


def _jsonschema_errors(
    instance: Any,
    schema: dict[str, Any],
    path: str,
    line: int,
) -> list[CheckError]:
    validator = Draft202012Validator(schema)
    out: list[CheckError] = []
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path) or "(root)"
        out.append(CheckError(path, line, f"front matter {loc}: {err.message}"))
    return out


def split_slides_with_lines(body: str, body_start_line: int) -> tuple[list[SlideSlice], list[CheckError]]:
    """Split body on lines that are exactly ---. Report empty trailing slides."""
    errors: list[CheckError] = []
    lines = body.splitlines()
    # If body is empty
    if not "".join(lines).strip():
        return [], errors

    slices: list[tuple[int, list[str]]] = []
    current: list[str] = []
    current_start = body_start_line
    line_no = body_start_line

    # Handle leading newlines in body — adjust start
    for i, line in enumerate(lines):
        if i == 0 and body.startswith("\n"):
            pass
        if line == "---":
            slices.append((current_start, current))
            current = []
            current_start = line_no + 1
        else:
            if not current and not line.strip():
                # skip leading blank lines inside a slice for start_line accuracy later
                current.append(line)
            else:
                current.append(line)
        line_no += 1
    slices.append((current_start, current))

    result: list[SlideSlice] = []
    for index, (start, raw_lines) in enumerate(slices, start=1):
        # Compute first non-empty line number
        first = start
        for offset, line in enumerate(raw_lines):
            if line.strip():
                first = start + offset
                break
        text = "\n".join(raw_lines).strip("\n")
        # Preserve whether content is empty
        if not text.strip():
            errors.append(
                CheckError(
                    "",
                    start,
                    f"slide {index} is empty "
                    f"(remove a trailing or duplicate --- separator)",
                )
            )
            continue
        result.append(SlideSlice(index=index, start_line=first, text=text.strip() + "\n"))
    return result, errors


def _relocate(errors: list[CheckError], path: str) -> list[CheckError]:
    return [CheckError(path, e.line, e.message) for e in errors]


def validate_slides_front_matter(
    loaded: Any,
    path: str,
    fm_line: int,
) -> list[CheckError]:
    errors: list[CheckError] = []
    if loaded is None:
        errors.append(CheckError(path, fm_line, "slides front matter is missing"))
        return errors
    if not isinstance(loaded, dict):
        errors.append(
            CheckError(path, fm_line, "slides front matter must be a YAML mapping")
        )
        return errors

    schema = load_schema("slides.schema.json")
    errors.extend(_jsonschema_errors(loaded, schema, path, fm_line))

    # Extra date calendar check (schema only checks pattern)
    raw_date = loaded.get("date")
    if isinstance(raw_date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
        try:
            date.fromisoformat(raw_date)
        except ValueError:
            errors.append(
                CheckError(path, fm_line, f"date is not a valid calendar day: {raw_date}")
            )

    unknown = sorted(set(loaded) - SLIDES_ALLOWED_KEYS)
    for key in unknown:
        errors.append(CheckError(path, fm_line, f"unknown slides front matter key: {key}"))
    return errors


def _is_valid_color(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(COLOR_RE.match(value.strip()))


def _is_valid_size(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        return bool(SIZE_STR_RE.match(value.strip()))
    return False


def _is_valid_font_weight(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return 100 <= value <= 900 and value % 100 == 0
    if isinstance(value, str):
        return value in {"normal", "bold", "bolder", "lighter"}
    return False


def _is_valid_line_height(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        return bool(re.match(r"^[0-9]+(\.[0-9]+)?(px|rem|em|%)?$", value.strip()))
    return False


def validate_style_tokens(tokens: Any, path: str, fm_line: int) -> list[CheckError]:
    errors: list[CheckError] = []
    if tokens is None:
        errors.append(CheckError(path, fm_line, "style front matter is missing"))
        return errors
    if not isinstance(tokens, dict):
        errors.append(
            CheckError(path, fm_line, "style front matter must be a YAML mapping")
        )
        return errors

    schema = load_schema("style.schema.json")
    errors.extend(_jsonschema_errors(tokens, schema, path, fm_line))

    unknown = sorted(set(tokens) - set(TOKEN_SPEC))
    for key in unknown:
        errors.append(CheckError(path, fm_line, f"unknown style token: {key}"))

    for key in sorted(REQUIRED_STYLE_TOKENS):
        if key not in tokens:
            errors.append(
                CheckError(path, fm_line, f"missing required style token: {key}")
            )

    # Stronger type messages (supplement schema)
    for key, value in tokens.items():
        if key not in TOKEN_SPEC:
            continue
        if key.startswith("color_"):
            if not _is_valid_color(value):
                errors.append(
                    CheckError(
                        path,
                        fm_line,
                        f"token {key}: invalid CSS colour: {value!r}",
                    )
                )
        elif key in {"font_weight_title", "font_weight_body"}:
            if not _is_valid_font_weight(value):
                errors.append(
                    CheckError(
                        path,
                        fm_line,
                        f"token {key}: invalid font weight: {value!r}",
                    )
                )
        elif key == "line_height":
            if not _is_valid_line_height(value):
                errors.append(
                    CheckError(
                        path,
                        fm_line,
                        f"token {key}: invalid line height: {value!r}",
                    )
                )
        elif key == "font_family":
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    CheckError(path, fm_line, f"token {key}: must be a non-empty string")
                )
        else:
            # sizes
            if key in TOKEN_SPEC and (
                key.startswith("font_size_")
                or key.startswith("page_")
                or key.endswith("_padding")
                or key.endswith("_width")
                or key.endswith("_height")
                or key.endswith("_radius")
                or key in {"gap", "border_width", "flow_node_min_width", "flow_node_padding"}
            ):
                if not _is_valid_size(value):
                    errors.append(
                        CheckError(
                            path,
                            fm_line,
                            f"token {key}: invalid size (positive number or value with px/rem/em/%): {value!r}",
                        )
                    )
    return errors


def _flow_nodes(body: str) -> tuple[list[str], list[str]]:
    """Return (nodes, empty_node_problems)."""
    nodes: list[str] = []
    problems: list[str] = []
    for line in body.splitlines():
        raw = line.strip()
        if not raw:
            continue
        if "->" in raw:
            parts = [p.strip() for p in raw.split("->")]
            for part in parts:
                if not part:
                    problems.append("empty flow node in arrow chain")
                else:
                    nodes.append(part)
        else:
            nodes.append(raw)
    return nodes, problems


def validate_slide_body(
    slide: SlideSlice,
    path: str,
    *,
    allow_html: bool,
) -> list[CheckError]:
    errors: list[CheckError] = []
    lines = slide.text.splitlines()
    base = slide.start_line

    # Track fenced code (``` / ~~~) and ::: blocks
    code_fence: str | None = None
    code_fence_line = 0
    block_kind: str | None = None
    block_start_line = 0
    block_lines: list[str] = []

    h1_lines: list[int] = []
    key_message_lines: list[int] = []
    heading_levels: list[tuple[int, int]] = []  # (line, level)

    def abs_line(i: int) -> int:
        return base + i

    i = 0
    while i < len(lines):
        line = lines[i]
        lineno = abs_line(i)

        if code_fence:
            if line.startswith(code_fence):
                code_fence = None
            i += 1
            continue

        ticks = FENCE_TICKS_RE.match(line)
        if ticks and block_kind is None:
            code_fence = ticks.group(1)[0] * len(ticks.group(1))
            code_fence_line = lineno
            i += 1
            continue

        # +++ only valid inside columns
        if line.strip() == "+++":
            if block_kind != "columns":
                errors.append(
                    CheckError(
                        path,
                        lineno,
                        "+++ column separator is only allowed inside a ::: columns block",
                    )
                )
            elif block_kind == "columns":
                block_lines.append(line)
            i += 1
            continue

        colon = COLON_FENCE_RE.match(line)
        if colon:
            colons, rest = colon.group(1), colon.group(2).strip()
            if len(colons) != 3:
                errors.append(
                    CheckError(
                        path,
                        lineno,
                        f"malformed fence opener/closer {colons!r} "
                        f"(use exactly three colons)",
                    )
                )
                i += 1
                continue

            if rest == "":
                # closer
                if block_kind is None:
                    errors.append(
                        CheckError(path, lineno, "stray closing ::: without an open block")
                    )
                else:
                    errors.extend(
                        _validate_block_content(
                            path,
                            block_kind,
                            block_start_line,
                            "\n".join(block_lines),
                        )
                    )
                    block_kind = None
                    block_lines = []
                i += 1
                continue

            # opener: ::: kind
            kind = rest.split()[0].lower() if rest.split() else ""
            extra = rest[len(kind) :].strip() if kind else rest
            if extra:
                errors.append(
                    CheckError(
                        path,
                        lineno,
                        f"malformed block opener; unexpected text after kind: {extra!r}",
                    )
                )
            if block_kind is not None:
                errors.append(
                    CheckError(
                        path,
                        lineno,
                        f"nested blocks are not allowed (already inside ::: {block_kind})",
                    )
                )
                i += 1
                continue
            if kind not in KNOWN_BLOCK_KINDS:
                errors.append(
                    CheckError(
                        path,
                        lineno,
                        f"unknown block kind {kind!r} "
                        f"(expected question, flow, or columns)",
                    )
                )
                # still enter a pseudo block so closer matches
                block_kind = kind or "unknown"
                block_start_line = lineno
                block_lines = []
                i += 1
                continue
            block_kind = kind
            block_start_line = lineno
            block_lines = []
            i += 1
            continue

        if block_kind is not None:
            # No H1 inside blocks
            if H1_RE.match(line):
                errors.append(
                    CheckError(
                        path,
                        lineno,
                        f"H1 is not allowed inside ::: {block_kind} blocks",
                    )
                )
            block_lines.append(line)
            i += 1
            continue

        # Outside blocks
        if KEY_MESSAGE_LINE_RE.match(line):
            key_message_lines.append(lineno)
            body = KEY_MESSAGE_LINE_RE.match(line).group("body").strip()  # type: ignore[union-attr]
            if not body:
                errors.append(CheckError(path, lineno, "Key Message body is empty"))

        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            heading_levels.append((lineno, level))
            if level == 1:
                h1_lines.append(lineno)

        if not allow_html and HTML_TAG_RE.search(line):
            # Allow backticks inline code containing tags
            if "`" not in line:
                errors.append(
                    CheckError(
                        path,
                        lineno,
                        "raw HTML is not allowed (pass --allow-html to permit it)",
                    )
                )

        # Table column consistency: gather contiguous table
        if TABLE_ROW_RE.match(line) or TABLE_SEP_RE.match(line):
            table_lines = []
            j = i
            while j < len(lines) and (
                TABLE_ROW_RE.match(lines[j]) or TABLE_SEP_RE.match(lines[j])
            ):
                table_lines.append((abs_line(j), lines[j]))
                j += 1
            errors.extend(_validate_table(path, table_lines))
            i = j
            continue

        # List indent: tabs forbidden; indent multiple of 2 or 3 spaces roughly
        if re.match(r"^[\t]+([-*+]|\d+\.)\s", line):
            errors.append(CheckError(path, lineno, "list item indented with tabs"))
        elif re.match(r"^ +([-*+]|\d+\.)\s", line):
            spaces = len(line) - len(line.lstrip(" "))
            if spaces % 2 != 0 and spaces % 3 != 0:
                errors.append(
                    CheckError(
                        path,
                        lineno,
                        f"list indent of {spaces} spaces is uneven "
                        f"(use multiples of 2 or 3)",
                    )
                )

        i += 1

    if code_fence is not None:
        errors.append(
            CheckError(
                path,
                code_fence_line,
                "unclosed fenced code block",
            )
        )
    if block_kind is not None:
        errors.append(
            CheckError(
                path,
                block_start_line,
                f"unclosed ::: {block_kind} block",
            )
        )

    if not h1_lines:
        errors.append(
            CheckError(path, base, f"slide {slide.index} is missing an H1 title (# ...)")
        )
    elif len(h1_lines) > 1:
        for lineno in h1_lines[1:]:
            errors.append(
                CheckError(
                    path,
                    lineno,
                    f"slide {slide.index} has more than one H1 title",
                )
            )

    if len(key_message_lines) > 1:
        for lineno in key_message_lines[1:]:
            errors.append(
                CheckError(
                    path,
                    lineno,
                    f"slide {slide.index} has more than one Key Message",
                )
            )

    # Heading hierarchy: no skipped levels (relative to previous heading in slide)
    prev_level: int | None = None
    for lineno, level in heading_levels:
        if prev_level is None:
            if level != 1:
                errors.append(
                    CheckError(
                        path,
                        lineno,
                        f"slide {slide.index} must start heading hierarchy at H1 "
                        f"(found H{level})",
                    )
                )
        elif level > prev_level + 1:
            errors.append(
                CheckError(
                    path,
                    lineno,
                    f"heading level skipped (H{prev_level} to H{level})",
                )
            )
        prev_level = level

    errors.extend(_pymarkdown_slide(path, slide))
    return errors


def _validate_block_content(
    path: str,
    kind: str,
    start_line: int,
    body: str,
) -> list[CheckError]:
    errors: list[CheckError] = []
    if kind not in KNOWN_BLOCK_KINDS:
        return errors
    if kind == "question":
        if not body.strip():
            errors.append(CheckError(path, start_line, "question block is empty"))
    elif kind == "flow":
        nodes, problems = _flow_nodes(body)
        for problem in problems:
            errors.append(CheckError(path, start_line, problem))
        if len(nodes) < 2:
            errors.append(
                CheckError(
                    path,
                    start_line,
                    "flow block needs at least two nodes (e.g. A -> B)",
                )
            )
    elif kind == "columns":
        cols = [c.strip() for c in re.split(r"\n\+\+\+\n", body.strip())]
        non_empty = [c for c in cols if c]
        if len(cols) < 2:
            errors.append(
                CheckError(
                    path,
                    start_line,
                    "columns block needs at least two columns separated by +++",
                )
            )
        elif len(non_empty) < 2:
            errors.append(
                CheckError(
                    path,
                    start_line,
                    "columns block has an empty column",
                )
            )
    return errors


def _table_width(line: str) -> int:
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return len(raw.split("|"))


def _validate_table(path: str, table_lines: list[tuple[int, str]]) -> list[CheckError]:
    errors: list[CheckError] = []
    if not table_lines:
        return errors
    widths = []
    for lineno, line in table_lines:
        if TABLE_SEP_RE.match(line):
            widths.append((lineno, _table_width(line)))
        elif TABLE_ROW_RE.match(line):
            widths.append((lineno, _table_width(line)))
    if not widths:
        return errors
    expected = widths[0][1]
    for lineno, width in widths[1:]:
        if width != expected:
            errors.append(
                CheckError(
                    path,
                    lineno,
                    f"table row has {width} columns, expected {expected}",
                )
            )
    return errors


def _pymarkdown_slide(path: str, slide: SlideSlice) -> list[CheckError]:
    """Run configured pymarkdown rules on one slide; map lines back to the file."""
    try:
        from pymarkdown.api import PyMarkdownApi
    except ImportError:
        return [
            CheckError(
                path,
                slide.start_line,
                "pymarkdownlnt is not installed; run uv sync",
            )
        ]

    api = PyMarkdownApi()
    for rule in PYMARKDOWN_DISABLE:
        api = api.disable_rule_by_identifier(rule)
    for rule in PYMARKDOWN_ENABLE:
        api = api.enable_rule_by_identifier(rule)

    # Strip ::: blocks for generic lint (deck-specific rules already checked them)
    scrubbed_lines = []
    in_block = False
    in_code = False
    code_mark = ""
    for line in slide.text.splitlines():
        if in_code:
            scrubbed_lines.append(line)
            if line.startswith(code_mark):
                in_code = False
            continue
        ticks = FENCE_TICKS_RE.match(line)
        if ticks and not in_block:
            in_code = True
            code_mark = ticks.group(1)[0] * len(ticks.group(1))
            scrubbed_lines.append(line)
            continue
        colon = COLON_FENCE_RE.match(line)
        if colon and len(colon.group(1)) == 3:
            rest = colon.group(2).strip()
            if rest == "":
                in_block = False
                scrubbed_lines.append("")  # keep line alignment
                continue
            in_block = True
            scrubbed_lines.append("")
            continue
        if in_block:
            scrubbed_lines.append("")
            continue
        scrubbed_lines.append(line)
    scrubbed = "\n".join(scrubbed_lines) + "\n"

    result = api.scan_string(scrubbed)
    errors: list[CheckError] = []
    for failure in result.scan_failures:
        # failure.line_number is 1-based within scrubbed string
        line = slide.start_line + failure.line_number - 1
        extra = failure.extra_error_information or ""
        msg = f"{failure.rule_id}: {failure.rule_description}{extra}"
        errors.append(CheckError(path, line, msg))
    for err in result.pragma_errors:
        errors.append(CheckError(path, slide.start_line, f"pymarkdown pragma: {err}"))
    for err in result.critical_errors:
        errors.append(CheckError(path, slide.start_line, f"pymarkdown: {err}"))
    return errors


def validate_assets(text: str, path: str, base_dir: Path, body_start_line: int) -> list[CheckError]:
    errors: list[CheckError] = []
    lines = text.splitlines()
    # Only scan body for links — approximate with whole file lines
    # Better: scan original file with line numbers
    full_lines = Path(path).read_text(encoding="utf-8").splitlines()
    in_code = False
    code_mark = ""
    for idx, line in enumerate(full_lines, start=1):
        if in_code:
            if line.startswith(code_mark):
                in_code = False
            continue
        ticks = FENCE_TICKS_RE.match(line)
        if ticks:
            in_code = True
            code_mark = ticks.group(1)[0] * len(ticks.group(1))
            continue
        for match in list(IMAGE_RE.finditer(line)) + list(LINK_RE.finditer(line)):
            target = match.group(1).strip()
            if not target or target.startswith("#"):
                continue
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                # scheme: http, https, mailto, data, …
                continue
            if target.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", target):
                errors.append(
                    CheckError(
                        path,
                        idx,
                        f"absolute local path is not allowed: {target}",
                    )
                )
                continue
            # relative
            asset = (base_dir / target).resolve()
            try:
                asset.relative_to(base_dir.resolve())
            except ValueError:
                errors.append(
                    CheckError(
                        path,
                        idx,
                        f"asset path escapes the slides directory: {target}",
                    )
                )
                continue
            if not asset.exists():
                errors.append(
                    CheckError(
                        path,
                        idx,
                        f"referenced asset does not exist: {target}",
                    )
                )
    return errors


def resolve_style_for_check(
    slides_path: Path,
    meta: dict[str, Any] | None,
    cli_style: Path | None,
) -> tuple[Path | None, list[CheckError]]:
    errors: list[CheckError] = []
    if cli_style is not None:
        path = cli_style
        if not path.is_file():
            errors.append(
                CheckError(str(cli_style), 1, f"style file not found: {cli_style}")
            )
            return None, errors
        return path.resolve(), errors

    if not meta or "style" not in meta:
        errors.append(
            CheckError(
                str(slides_path),
                1,
                "no style file: set style: in slides front matter or pass --style",
            )
        )
        return None, errors

    rel = Path(str(meta["style"]))
    path = rel if rel.is_absolute() else (slides_path.parent / rel)
    if rel.is_absolute() or str(meta["style"]).startswith("/"):
        errors.append(
            CheckError(
                str(slides_path),
                1,
                f"style path must be relative to the slides file: {meta['style']}",
            )
        )
    if not path.is_file():
        errors.append(
            CheckError(
                str(slides_path),
                1,
                f"style file not found: {meta['style']}",
            )
        )
        return None, errors
    return path.resolve(), errors


def check_deck(
    slides_path: Path,
    style_path: Path | None = None,
    *,
    allow_html: bool = False,
) -> list[CheckError]:
    """Validate slides (+ style). Returns all errors; empty means OK."""
    path = str(slides_path)
    errors: list[CheckError] = []

    if not slides_path.is_file():
        return [CheckError(path, 1, f"slides file not found: {slides_path}")]

    text = slides_path.read_text(encoding="utf-8")
    loaded, fm_line, body_start, body, yaml_errors = _yaml_front_matter(text)
    errors.extend(_relocate(yaml_errors, path))

    meta: dict[str, Any] | None
    if loaded is None and not yaml_errors:
        # No front matter at all
        errors.append(CheckError(path, 1, "slides front matter is missing"))
        meta = None
    elif not isinstance(loaded, dict) and loaded is not None:
        errors.append(
            CheckError(path, fm_line, "slides front matter must be a YAML mapping")
        )
        meta = None
    else:
        meta = loaded if isinstance(loaded, dict) else None
        if meta is not None:
            errors.extend(validate_slides_front_matter(meta, path, fm_line))

    slides, split_errors = split_slides_with_lines(body, body_start)
    errors.extend(_relocate(split_errors, path))
    if not slides and not any("empty" in e.message for e in split_errors):
        errors.append(CheckError(path, body_start, "no slides found"))

    for slide in slides:
        errors.extend(validate_slide_body(slide, path, allow_html=allow_html))

    errors.extend(validate_assets(text, path, slides_path.parent, body_start))

    resolved_style, style_resolve_errors = resolve_style_for_check(
        slides_path, meta, style_path
    )
    errors.extend(style_resolve_errors)

    if resolved_style is not None:
        style_text = resolved_style.read_text(encoding="utf-8")
        style_loaded, style_fm_line, _, _, style_yaml_errors = _yaml_front_matter(
            style_text
        )
        style_path_str = str(resolved_style)
        errors.extend(_relocate(style_yaml_errors, style_path_str))
        if style_loaded is None and not style_yaml_errors:
            errors.append(
                CheckError(style_path_str, 1, "style front matter is missing")
            )
        else:
            errors.extend(
                validate_style_tokens(style_loaded, style_path_str, style_fm_line)
            )

    return sort_errors(errors)


def format_errors(errors: list[CheckError]) -> str:
    return "\n".join(e.format() for e in errors)
