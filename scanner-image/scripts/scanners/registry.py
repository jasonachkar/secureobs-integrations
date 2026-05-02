"""Driver registry for the scanner orchestrator.

Adding a new scanner:

1. Implement ``run(workspace, project_id, pipeline_run_id, config)`` in
   ``scanners/<module>.py`` returning ``ScanResult`` with payloads shaped for
   ``POST /api/findings/bulk-universal`` (camelCase JSON — see backend
   ``UniversalFindingDto``) **or**, for legacy Semgrep/GitLeaks, the dedicated
   bulk endpoints shown below.

2. Register the catalog ``key``, ``bulk_endpoint``, and runner here.

``bulk-universal`` is the ingestion path for Trivy, Bandit, Checkov, … — one
consistent DTO regardless of tooling. Keys must match backend ``Scanner.Key``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from . import bandit, checkov, eslint_security, gitleaks, osv_scanner, semgrep, trivy
from .base import ScanResult

log = logging.getLogger(__name__)

DriverRunner = Callable[[str, str, str, "dict[str, str] | None"], ScanResult]

_BULK_UNIVERSAL = "findings/bulk-universal"


@dataclass(frozen=True)
class Driver:
    key: str
    bulk_endpoint: str
    runner: DriverRunner


def _semgrep_runner(w: str, p: str, r: str, c: dict | None) -> ScanResult:
    return semgrep.run(w, p, r, c)


def _gitleaks_runner(w: str, p: str, r: str, c: dict | None) -> ScanResult:
    return gitleaks.run(w, p, r, c)


def _trivy_runner(w: str, p: str, r: str, c: dict | None) -> ScanResult:
    return trivy.run(w, p, r, c)


def _bandit_runner(w: str, p: str, r: str, c: dict | None) -> ScanResult:
    return bandit.run(w, p, r, c)


def _checkov_runner(w: str, p: str, r: str, c: dict | None) -> ScanResult:
    return checkov.run(w, p, r, c)


def _osv_runner(w: str, p: str, r: str, c: dict | None) -> ScanResult:
    return osv_scanner.run(w, p, r, c)


def _eslint_runner(w: str, p: str, r: str, c: dict | None) -> ScanResult:
    return eslint_security.run(w, p, r, c)


def _external_toolchain_stub(key: str) -> DriverRunner:
    """Sonar / Snyk / CodeQL / ZAP need hosted auth or vendor-specific CI steps."""

    def _run(
        workspace: str,
        project_id: str,
        pipeline_run_id: str,
        config: dict | None,
    ) -> ScanResult:
        del workspace, project_id, pipeline_run_id, config
        log.info(
            "Skipping '%s' — not bundled in this image; wire it through your "
            "vendor's CI (token, SARIF, or AST analysis) instead of expecting "
            "the generic orchestrator bundle to run it.",
            key,
        )
        return ScanResult(skipped=True, skip_reason="external_toolchain")

    return _run


REGISTRY: dict[str, Driver] = {
    "semgrep": Driver("semgrep", "findings/bulk-semgrep", _semgrep_runner),
    "gitleaks": Driver("gitleaks", "findings/bulk-gitleaks", _gitleaks_runner),
    "trivy": Driver("trivy", _BULK_UNIVERSAL, _trivy_runner),
    "bandit": Driver("bandit", _BULK_UNIVERSAL, _bandit_runner),
    "eslint-security": Driver("eslint-security", _BULK_UNIVERSAL, _eslint_runner),
    "osv-scanner": Driver("osv-scanner", _BULK_UNIVERSAL, _osv_runner),
    "checkov": Driver("checkov", _BULK_UNIVERSAL, _checkov_runner),
    "codeql": Driver("codeql", _BULK_UNIVERSAL, _external_toolchain_stub("codeql")),
    "sonarqube": Driver("sonarqube", _BULK_UNIVERSAL, _external_toolchain_stub("sonarqube")),
    "snyk": Driver("snyk", _BULK_UNIVERSAL, _external_toolchain_stub("snyk")),
    "owasp-zap": Driver("owasp-zap", _BULK_UNIVERSAL, _external_toolchain_stub("owasp-zap")),
}

DEFAULT_KEYS: list[str] = ["semgrep", "gitleaks"]
