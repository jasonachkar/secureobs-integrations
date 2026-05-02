# Changelog

## v1.1.0 — 2026-05-02

Dynamic scanner selection.

- The `scan` subcommand now calls `GET /api/projects/{projectId}/scanners/active` at the start of every run and executes only the scanners the user has enabled in the SecureObs dashboard. Pipeline YAML stays identical for every project — adding or removing a scanner from the dashboard takes effect on the next CI run with **zero pipeline edits**.
- New driver registry (`scanners/registry.py`) maps catalog keys to runner modules. Stubs are registered for every catalog row whose driver isn't bundled in this image yet (Trivy, Bandit, ESLint Security, OSV-Scanner, Checkov, CodeQL, SonarQube, Snyk, OWASP ZAP) — enabling them in the dashboard logs a clear "driver not implemented yet" line and skips, so users can opt in early without breaking their pipeline.
- Defensive fallback: if the active-scanners endpoint is unreachable (network / 5xx), the orchestrator falls back to the default set (`semgrep`, `gitleaks`) so a degraded control plane never breaks a user's pipeline. Auth failures and unknown projects still abort hard with exit code 1.
- Scanner runner signature extended with an optional `config` argument (per-project tuning surfaced from `ProjectScanner.Config`). Unused for Semgrep and GitLeaks today; reserved for Sonar URL, custom rulesets, allowlists, etc.
- Catalog-vs-image skew is handled gracefully in both directions: unknown keys returned by the API are skipped with a warning ("image is older than catalog"), and known-but-unimplemented catalog keys log a friendly notice ("driver ships in a later tag").

## v1.0.0 — 2026-04-27

Initial release.

- Bundled Docker image with Semgrep (p/ci ruleset) and GitLeaks v8.21.2
- `scan` subcommand: runs both scanners against `/workspace`, posts findings to SecureObs API
- `gate` subcommand: queries API for blocking findings, exits 3 if blocked
- `pr-comment` subcommand: posts or updates a single PR comment with scan status (Azure DevOps and GitHub Actions)
- Marker-based comment deduplication — one comment per PR, updated on each run
- Structured logging to stderr; `SECUREOBS_DEBUG=1` enables verbose output
- Retry logic on transient API errors (3 attempts, exponential backoff)
