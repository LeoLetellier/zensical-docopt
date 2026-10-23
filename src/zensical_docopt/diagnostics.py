from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A problem found while parsing. `line` is 1-based within the docstring."""

    code: str
    message: str
    severity: Severity = Severity.WARNING
    line: int | None = None

    def format(self, origin: str = "<docstring>") -> str:
        where = f"{origin}:{self.line}" if self.line else origin
        return f"{where}: {self.severity.value} {self.code}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "line": self.line,
        }
