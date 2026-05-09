from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScanResult:
    findings: list[dict[str, Any]] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""
    # Populated when skipped due to a non-zero tool exit so cli.py can
    # surface the failure at ERROR level with full diagnostic context.
    exit_code: int | None = None
    stderr_tail: str = ""
