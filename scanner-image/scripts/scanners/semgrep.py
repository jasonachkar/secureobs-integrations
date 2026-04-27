import json
import logging
import os
import subprocess
import sys

from .base import ScanResult

log = logging.getLogger(__name__)

_RESULTS_FILE = "/tmp/secureobs-semgrep.json"


def run(source_dir: str, project_id: str, pipeline_run_id: str) -> ScanResult:
    log.info("Running Semgrep on %s", source_dir)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"

    proc = subprocess.run(
        ["semgrep", "scan", "--config", "p/ci", "--json", "--output", _RESULTS_FILE, source_dir],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )

    # semgrep exits 0 (clean) or 1 (findings found) — both are success
    if proc.returncode not in (0, 1):
        log.error("Semgrep exited with unexpected code %d: %s", proc.returncode, proc.stderr[:500])
        sys.exit(2)

    if not os.path.exists(_RESULTS_FILE):
        log.info("Semgrep produced no results file — treating as clean.")
        return ScanResult(skipped=True, skip_reason="no results file")

    with open(_RESULTS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    raw_results = data.get("results", [])
    log.info("Semgrep found %d raw result(s)", len(raw_results))

    findings = []
    for r in raw_results:
        extra = r.get("extra", {})
        metadata = extra.get("metadata", {})
        findings.append({
            "checkId": r.get("check_id", ""),
            "path": r.get("path", ""),
            "startLine": r.get("start", {}).get("line", 0),
            "endLine": r.get("end", {}).get("line", 0),
            "severity": extra.get("severity", ""),
            "message": extra.get("message", ""),
            # try extra.cwe first (older semgrep), fall back to extra.metadata.cwe
            "cwe": extra.get("cwe") or metadata.get("cwe", []),
            "owasp": extra.get("owasp") or metadata.get("owasp", []),
            "projectId": project_id,
            "pipelineRunId": pipeline_run_id,
        })

    return ScanResult(findings=findings)
