from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScanResult:
    findings: list[dict[str, Any]] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""
