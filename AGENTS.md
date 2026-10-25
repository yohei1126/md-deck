# AGENTS.md

Guidance for coding agents working on **md-deck** (Markdown → 16:9 PDF generator and GitHub Action).

## What this repo is

- Layout, validation, rendering, and the reusable Action live here.
- Real slide content, `deck_style.md`, brand CSS, and Release PDFs live in **deck repositories**, not here.
- `examples/` is sample input only.

## Slide-deck practice (read this)

When creating or revising decks that **use** md-deck (including work in other repos), follow:

**[md-deck skill (yohei1126/agent-skills)](https://github.com/yohei1126/agent-skills/blob/main/md-deck/SKILL.md)**

That skill covers workflow, style vs content, spacing/density, review before tag/release, and common failures. Do not invent unsupported Markdown directives.

## Docs in this repo

| Doc | Topic |
| :--- | :--- |
| [README.md](README.md) | Install, CLI, Action |
| [docs/INPUT_FORMAT.md](docs/INPUT_FORMAT.md) | Slides contract and flow syntax |
| [docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md) / [STYLE_GUIDE.ja.md](docs/STYLE_GUIDE.ja.md) | Style tokens |
| [docs/HOOKS.md](docs/HOOKS.md) | Stable CSS hooks |

## Agent constraints

- Prefer PRs over direct pushes to the default branch.
- Pin Action consumers to a release tag or full commit SHA (never a floating major that can break CI).
- Do not cut tags/releases unless the owner asked.
- Do not put customer or proposal content into this repository.
