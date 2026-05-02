"""Driver registry for the scanner orchestrator.

Adding a new scanner is a two-step change:

1. Implement a runner module under ``scanners/`` that exposes
   ``run(workspace, project_id, pipeline_run_id, config) -> ScanResult``.
2. Register it here with its catalog ``key`` and the bulk-add endpoint that
   accepts its findings payload.

Catalog keys MUST match the ``Key`` column of the backend ``Scanners`` table
exactly — the orchestrator looks up drivers by the keys returned from
``GET /api/projects/{id}/scanners/active``. Catalog rows whose driver isn't
implemented in this image yet are mapped to a stub that logs a warning and
skips, so newer catalog rows pushed by SecureObs ops never break older pinned
image tags. Conversely, unknown keys (e.g. an old image hitting a brand-new
catalog row before its driver has been deployed) are also skipped with a
warning rather than aborting the whole scan.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from . import gitleaks, semgrep
from .base import ScanResult

log = logging.getLogger(__name__)

# Signature of every driver runner. ``config`` is whatever the user stored in
# ``ProjectScanner.Config`` for this scanner (e.g. a SonarQube URL). It's
# typed permissively because the API may legitimately return ``None`` when no
# config is set.
DriverRunner = Callable[[str, str, str, "dict[str, str] | None"], ScanResult]


@dataclass(frozen=True)
class Driver:
    """A single registered scanner driver.

    Attributes:
        key: Catalog key — must match the backend ``Scanner.Key`` exactly.
        bulk_endpoint: Path (relative to ``SECUREOBS_API_URL``) to POST findings to.
        runner: Callable that executes the scanner against ``/workspace``.
    """

    key: str
    bulk_endpoint: str
    runner: DriverRunner


def _semgrep_runner(
    workspace: str,
    project_id: str,
    pipeline_run_id: str,
    config: "dict[str, str] | None",
) -> ScanResult:
    return semgrep.run(workspace, project_id, pipeline_run_id, config)


def _gitleaks_runner(
    workspace: str,
    project_id: str,
    pipeline_run_id: str,
    config: "dict[str, str] | None",
) -> ScanResult:
    return gitleaks.run(workspace, project_id, pipeline_run_id, config)


def _make_stub(key: str) -> DriverRunner:
    """Driver placeholder for catalog rows whose driver isn't bundled yet.

    Returning a skipped ``ScanResult`` (instead of raising) means a user who
    enables a not-yet-implemented scanner just gets a clear log line and the
    rest of their scan still runs — strictly better than blowing up the whole
    pipeline.
    """

    def _run(
        workspace: str,
        project_id: str,
        pipeline_run_id: str,
        config: "dict[str, str] | None",
    ) -> ScanResult:
        log.warning(
            "Scanner '%s' is in the catalog but its driver isn't bundled in "
            "this image yet — skipping. Pin to a newer image tag once the "
            "driver ships.",
            key,
        )
        return ScanResult(skipped=True, skip_reason="driver_not_implemented")

    return _run


# The bulk endpoint for stubs is intentionally the same shape as a real one;
# the orchestrator never calls it because stubs always return skipped=True.
_STUB_ENDPOINT = "findings/bulk-noop"


REGISTRY: dict[str, Driver] = {
    "semgrep": Driver("semgrep", "findings/bulk-semgrep", _semgrep_runner),
    "gitleaks": Driver("gitleaks", "findings/bulk-gitleaks", _gitleaks_runner),
    # Catalog parity stubs — rows seeded in SecureObsDbContext that don't yet
    # have a driver bundled in this image. They no-op safely so users can
    # enable them in the dashboard without breaking their pipeline.
    "trivy": Driver("trivy", _STUB_ENDPOINT, _make_stub("trivy")),
    "bandit": Driver("bandit", _STUB_ENDPOINT, _make_stub("bandit")),
    "eslint-security": Driver(
        "eslint-security", _STUB_ENDPOINT, _make_stub("eslint-security")
    ),
    "osv-scanner": Driver("osv-scanner", _STUB_ENDPOINT, _make_stub("osv-scanner")),
    "checkov": Driver("checkov", _STUB_ENDPOINT, _make_stub("checkov")),
    "codeql": Driver("codeql", _STUB_ENDPOINT, _make_stub("codeql")),
    "sonarqube": Driver("sonarqube", _STUB_ENDPOINT, _make_stub("sonarqube")),
    "snyk": Driver("snyk", _STUB_ENDPOINT, _make_stub("snyk")),
    "owasp-zap": Driver("owasp-zap", _STUB_ENDPOINT, _make_stub("owasp-zap")),
}

# Used when the API call to fetch active scanners fails (network blip, 5xx).
# Mirrors the backend ``ScannerCatalogService.DefaultScannerKeys`` so a degraded
# control plane still produces a meaningful scan.
DEFAULT_KEYS: list[str] = ["semgrep", "gitleaks"]
