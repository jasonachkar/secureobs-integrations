"""Checkov -> universal findings (best-effort JSON parse across versions)."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile

from .base import ScanResult

log = logging.getLogger(__name__)


def _fp(*parts: str) -> str:
    s = "|".join(str(p or "") for p in parts).encode()
    return base64.b64encode(hashlib.sha256(s).digest()).decode().strip()


def _iter_failed_checks(obj) -> list[dict]:
    """Extract failed_checks from nested Checkov JSON."""
    out: list[dict] = []
    if obj is None:
        return out
    if isinstance(obj, list):
        for item in obj:
            out.extend(_iter_failed_checks(item))
        return out
    if isinstance(obj, dict):
        fc = obj.get("failed_checks")
        if isinstance(fc, list):
            for c in fc:
                if isinstance(c, dict):
                    out.append(c)
        for v in obj.values():
            if isinstance(v, (dict, list)):
                out.extend(_iter_failed_checks(v))
    return out


def run(
    source_dir: str,
    project_id: str,
    pipeline_run_id: str,
    config: dict[str, str] | None = None,
) -> ScanResult:
    del config
    log.info("Running Checkov on %s", source_dir)

    tmpdir = tempfile.mkdtemp(prefix="secureobs-checkov-")
    data = None

    try:
        proc = subprocess.run(
            [
                "checkov",
                "-d",
                source_dir,
                "--quiet",
                "-o",
                "json",
                "--output-file-path",
                tmpdir,
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode not in (0, 1):
            log.error(
                "Checkov exited %d: %s",
                proc.returncode,
                (proc.stderr or proc.stdout or "")[:800],
            )
            sys.exit(2)

        results_path = os.path.join(tmpdir, "results.json")
        if os.path.isfile(results_path):
            with open(results_path, encoding="utf-8") as f:
                data = json.load(f)
        elif proc.stdout.strip():
            data = json.loads(proc.stdout)
        else:
            json_files = [
                os.path.join(tmpdir, f)
                for f in os.listdir(tmpdir)
                if f.endswith(".json") and "checkov" not in f.lower()
            ]
            if json_files:
                with open(json_files[0], encoding="utf-8") as f:
                    data = json.load(f)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if data is None:
        return ScanResult(skipped=True, skip_reason="checkov wrote no JSON")

    failed = _iter_failed_checks(data)

    findings: list[dict] = []
    for c in failed:
        cid = c.get("check_id") or "CKV"
        sev_raw = str(c.get("severity") or c.get("Check_Severity") or "MEDIUM")
        name = str(c.get("check_name") or cid)
        fpath = c.get("file_path") or ""
        rl = c.get("file_line_range")
        start = end_line = None
        if isinstance(rl, list) and len(rl) >= 1:
            try:
                start = int(rl[0])
            except (ValueError, TypeError):
                start = None
            if len(rl) >= 2:
                try:
                    end_line = int(rl[1])
                except (ValueError, TypeError):
                    end_line = start

        desc = "\n".join(
            filter(
                None,
                [
                    name,
                    str(c.get("guideline") or ""),
                    str(c.get("resource") or c.get("check_class") or ""),
                ],
            )
        )

        fingerprint = _fp("checkov", cid, str(fpath), str(start))

        findings.append(
            {
                "scanner": "checkov",
                "ruleId": cid,
                "filePath": str(fpath) or None,
                "codeSnippet": None,
                "severity": sev_raw.upper(),
                "description": desc or cid,
                "cweIds": None,
                "owaspCategories": None,
                "startLine": start,
                "endLine": end_line or start,
                "projectId": project_id,
                "pipelineRunId": pipeline_run_id,
                "fingerprint": fingerprint,
                "rawPayload": json.dumps(c, separators=(",", ":"))[:80_000],
            }
        )

    log.info("Checkov produced %d finding row(s)", len(findings))
    return ScanResult(findings=findings)
