"""Structured check errors reported as file:line: message."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckError:
    path: str
    line: int
    message: str

    def format(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def sort_errors(errors: list[CheckError]) -> list[CheckError]:
    return sorted(errors, key=lambda e: (e.path, e.line, e.message))
