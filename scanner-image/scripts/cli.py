#!/usr/bin/env python3
import argparse
import logging
import sys

import config
import api_client
import build_gate as gate_module
from scanners import semgrep, gitleaks
from pr_comments import azuredevops, github

log = logging.getLogger(__name__)


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--project-id", required=True, help="SecureObs project ID")
    p.add_argument("--tenant-id", required=True, help="SecureObs tenant ID")
    p.add_argument("--pipeline-run-id", required=True, help="Unique pipeline run identifier")


def cmd_scan(args: argparse.Namespace) -> None:
    api_url = config.get_api_url()
    api_key = config.require_env("SECUREOBS_API_KEY")

    semgrep_result = semgrep.run("/workspace", args.project_id, args.pipeline_run_id)
    if semgrep_result.findings:
        data = api_client.post_findings(api_url, api_key, "findings/bulk-semgrep", semgrep_result.findings)
        ingested = data.get("ingested", len(semgrep_result.findings))
        deduped = data.get("deduplicated", 0)
        log.info("Semgrep: %d finding(s) ingested (%d new after dedup).", ingested, deduped)
    else:
        log.info("Semgrep: no findings.")

    gitleaks_result = gitleaks.run("/workspace", args.project_id, args.pipeline_run_id)
    if gitleaks_result.findings:
        data = api_client.post_findings(api_url, api_key, "findings/bulk-gitleaks", gitleaks_result.findings)
        ingested = data.get("ingested", len(gitleaks_result.findings))
        log.info("GitLeaks: %d secret(s) ingested.", ingested)
    else:
        log.info("GitLeaks: no secrets found.")

    log.info("Scan complete.")


def cmd_gate(args: argparse.Namespace) -> None:
    api_url = config.get_api_url()
    api_key = config.require_env("SECUREOBS_API_KEY")
    gate_module.run(api_url, api_key, args.pipeline_run_id)


def cmd_pr_comment(args: argparse.Namespace) -> None:
    api_url = config.get_api_url()
    api_key = config.require_env("SECUREOBS_API_KEY")

    if args.platform == "azuredevops":
        azuredevops.post_or_update(api_url, api_key, args.pipeline_run_id)
    elif args.platform == "github":
        github.post_or_update(api_url, api_key, args.pipeline_run_id)
    else:
        log.error("Unknown platform: %s", args.platform)
        sys.exit(1)


def main() -> None:
    config.setup_logging()

    parser = argparse.ArgumentParser(
        prog="secureobs-scanner",
        description="SecureObs security scanner for CI pipelines.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan_p = sub.add_parser("scan", help="Run Semgrep and GitLeaks, post findings to SecureObs.")
    _add_common_args(scan_p)

    gate_p = sub.add_parser("gate", help="Check for blocking findings. Exits 3 if blocked.")
    _add_common_args(gate_p)

    pr_p = sub.add_parser("pr-comment", help="Post or update a PR comment with scan results.")
    _add_common_args(pr_p)
    pr_p.add_argument(
        "--platform",
        required=True,
        choices=["azuredevops", "github"],
        help="CI platform for PR comment posting.",
    )

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "gate":
        cmd_gate(args)
    elif args.command == "pr-comment":
        cmd_pr_comment(args)


if __name__ == "__main__":
    main()
