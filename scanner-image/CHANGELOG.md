# Changelog

## v1.0.0 — 2026-04-27

Initial release.

- Bundled Docker image with Semgrep (p/ci ruleset) and GitLeaks v8.21.2
- `scan` subcommand: runs both scanners against `/workspace`, posts findings to SecureObs API
- `gate` subcommand: queries API for blocking findings, exits 3 if blocked
- `pr-comment` subcommand: posts or updates a single PR comment with scan status (Azure DevOps and GitHub Actions)
- Marker-based comment deduplication — one comment per PR, updated on each run
- Structured logging to stderr; `SECUREOBS_DEBUG=1` enables verbose output
- Retry logic on transient API errors (3 attempts, exponential backoff)
