#!/usr/bin/env python3
import argparse
import logging
import sys

import config
import api_client
import build_gate as gate_module
from scanners.registry import DEFAULT_KEYS, REGISTRY
from pr_comments import azuredevops, github

log = logging.getLogger(__name__)


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--project-id", required=True, help="SecureObs project ID")
    p.add_argument("--tenant-id", required=True, help="SecureObs tenant ID")
    p.add_argument("--pipeline-run-id", required=True, help="Unique pipeline run identifier")


def _resolve_active_scanners(
    api_url: str, api_key: str, project_id: str
) -> list[dict]:
    """Decide which scanners to run on this invocation.

    Source of truth is the SecureObs API — whatever the user toggled in the
    dashboard takes effect on the next pipeline run with zero YAML edits. If
    that lookup is degraded (transient 5xx, network blip), we fall back to a
    safe default set so the user still gets *some* scan rather than a broken
    pipeline. Auth/permission failures are NOT silently masked here — those
    bubble out of ``api_client.get_active_scanners`` as ``sys.exit(1)``.
    """
    active = api_client.get_active_scanners(api_url, api_key, project_id)
    if active is None:
        log.warning(
            "Falling back to default scanners: %s. Toggle scanners in the "
            "SecureObs dashboard to override on the next run.",
            ", ".join(DEFAULT_KEYS),
        )
        return [{"key": k, "config": None} for k in DEFAULT_KEYS]
    return active


def cmd_scan(args: argparse.Namespace) -> None:
    api_url = config.get_api_url()
    api_key = config.require_env("SECUREOBS_API_KEY")

    active = _resolve_active_scanners(api_url, api_key, args.project_id)

    if not active:
        log.warning(
            "No scanners are enabled for this project. Enable at least one "
            "in the SecureObs dashboard, then re-run the pipeline."
        )
        return

    enabled_keys = [str(entry.get("key", "?")) for entry in active]
    log.info("Active scanners for this run: %s", ", ".join(enabled_keys))

    for entry in active:
        key = entry.get("key")
        cfg = entry.get("config") or None

        if not key or not isinstance(key, str):
            log.warning("Skipping malformed active-scanner entry: %r", entry)
            continue

        driver = REGISTRY.get(key)
        if driver is None:
            log.warning(
                "Unknown scanner key '%s' returned by the API; skipping. "
                "(This usually means the SecureObs catalog is ahead of this "
                "image — pin to a newer tag once the driver ships.)",
                key,
            )
            continue

        try:
            result = driver.runner(
                "/workspace", args.project_id, args.pipeline_run_id, cfg
            )
        except Exception:
            # Defensive: a driver crash must never take down the whole scan.
            # Auth/network failures inside the bulk-add path still abort via
            # ``post_findings`` (sys.exit), which is the desired blast radius.
            log.exception(
                "Scanner '%s' raised an unexpected error; continuing with the "
                "remaining scanners.",
                key,
            )
            continue

        if result.skipped:
            if result.exit_code is not None:
                log.error(
                    "%s skipped due to non-zero exit (code %d): %s. stderr: %s",
                    key,
                    result.exit_code,
                    result.skip_reason or "(no reason given)",
                    result.stderr_tail or "(none)",
                )
            else:
                log.info("%s skipped: %s", key, result.skip_reason or "(no reason given)")
            continue

        if not result.findings:
            log.info("%s: no findings.", key)
            continue

        data = api_client.post_findings(api_url, api_key, driver.bulk_endpoint, result.findings)
        ingested = data.get("ingested", len(result.findings))
        deduped = data.get("deduplicated", 0)
        log.info("%s: %d finding(s) ingested (%d new after dedup).", key, ingested, deduped)

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

    scan_p = sub.add_parser(
        "scan",
        help="Run the scanners enabled for this project in the SecureObs dashboard, then post findings.",
    )
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
