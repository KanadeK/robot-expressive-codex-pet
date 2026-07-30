"""Structured validation reports with stable machine-readable issue codes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True, slots=True)
class Issue:
    severity: Severity
    code: str
    message: str
    location: str | None = None


@dataclass(slots=True)
class ValidationReport:
    target: Path
    issues: list[Issue] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(issue.severity == "error" for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.severity == "warning" for issue in self.issues)

    def add(
        self,
        severity: Severity,
        code: str,
        message: str,
        location: str | None = None,
    ) -> None:
        self.issues.append(Issue(severity, code, message, location))

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "target": str(self.target),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "metadata": self.metadata,
            "issues": [asdict(issue) for issue in self.issues],
        }

    def format_text(self) -> str:
        verdict = "PASS" if self.ok else "FAIL"
        lines = [
            f"{verdict}: {self.target}",
            f"errors={self.error_count} warnings={self.warning_count}",
        ]
        for issue in self.issues:
            where = f" [{issue.location}]" if issue.location else ""
            lines.append(f"{issue.severity.upper()} {issue.code}{where}: {issue.message}")
        return "\n".join(lines)
