# secureobs/scanner

Docker image bundling Semgrep, GitLeaks, Trivy, Bandit, Checkov, OSV-Scanner, ESLint (security plugin), and SecureObs orchestration logic for CI pipelines.

**Docker Hub:** `secureobs/scanner`

---

## Quick start

```bash
docker run --rm \
  -v $(pwd):/workspace \
  -e SECUREOBS_API_KEY=your-key \
  secureobs/scanner:v1 \
  scan \
  --project-id your-project-id \
  --tenant-id your-tenant-id \
  --pipeline-run-id unique-run-id
```

---

## Subcommands

### `scan`

Runs the scanners that are currently enabled for `--project-id` against `/workspace`, then posts findings to SecureObs. The image fetches the enabled list from `GET /api/projects/{projectId}/scanners/active` at the start of every run, so toggling a scanner in the SecureObs dashboard takes effect on the next CI run with **zero pipeline-YAML edits**. If the API is unreachable, the orchestrator falls back to a built-in safe default (`semgrep` + `gitleaks`) so a degraded control plane never breaks the pipeline.

```bash
docker run --rm \
  -v /path/to/code:/workspace \
  -e SECUREOBS_API_KEY=<key> \
  secureobs/scanner:v1 \
  scan \
  --project-id <project-id> \
  --tenant-id <tenant-id> \
  --pipeline-run-id <unique-run-id>
```

**Rollout:** your SecureObs backend must expose `POST /api/findings/bulk-universal` (API key authenticated) **before** you rely on scanners other than Semgrep/GitLeaks. Otherwise only the typed Semgrep/GitLeaks bulk endpoints succeed.

Bundled scanners (as of **v1.2+**):

| Catalog key | In image? | Bulk ingest endpoint |
|---|---|---|
| `semgrep` | Yes | `/api/findings/bulk-semgrep` |
| `gitleaks` | Yes | `/api/findings/bulk-gitleaks` |
| `trivy`, `bandit`, `checkov`, `osv-scanner`, `eslint-security` | Yes | `/api/findings/bulk-universal` |
| `codeql`, `sonarqube`, `snyk`, `owasp-zap` | **Skipped** — need vendor toolchain / secrets / SARIF beyond a generic tarball scan | _(no ingest from this bundle)_ |

`eslint-security` only analyses plain JavaScript family files (`*.js`, `*.jsx`, `*.mjs`, `*.cjs`) via the bundled recommended ruleset — TypeScript-heavy repos may prefer their own ESLint CI step separately.

### `gate`

Queries SecureObs for blocking findings on this pipeline run. Exits 0 if clean, **exits 3 if blocked**.

```bash
docker run --rm \
  -e SECUREOBS_API_KEY=<key> \
  secureobs/scanner:v1 \
  gate \
  --project-id <project-id> \
  --tenant-id <tenant-id> \
  --pipeline-run-id <unique-run-id>
```

### `pr-comment`

Posts or updates a single PR comment with the scan status. Detects existing SecureObs comments via an HTML marker and updates in place rather than creating duplicates.

```bash
docker run --rm \
  -e SECUREOBS_API_KEY=<key> \
  -e SYSTEM_ACCESSTOKEN=<ado-token> \
  -e SYSTEM_PULLREQUEST_PULLREQUESTID=<pr-id> \
  -e BUILD_REPOSITORY_ID=<repo-id> \
  -e SYSTEM_TEAMPROJECT=<project> \
  -e SYSTEM_TEAMFOUNDATIONCOLLECTIONURI=<collection-uri> \
  secureobs/scanner:v1 \
  pr-comment \
  --project-id <project-id> \
  --tenant-id <tenant-id> \
  --pipeline-run-id <unique-run-id> \
  --platform azuredevops
```

For GitHub Actions, use `--platform github` with `GH_TOKEN`, `GITHUB_REPOSITORY`, `GITHUB_EVENT_NAME`, and `GITHUB_REF`.

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECUREOBS_API_KEY` | Yes | — | API key from your SecureObs tenant |
| `SECUREOBS_API_URL` | No | `https://secureobs-dashboard.azurewebsites.net/api` | Override API base URL |
| `SECUREOBS_DEBUG` | No | — | Set to `1` for verbose debug logging |

### Additional variables for `pr-comment --platform azuredevops`

| Variable | Source |
|---|---|
| `SYSTEM_ACCESSTOKEN` | Azure Pipelines automatic (requires "Allow scripts to access OAuth token") |
| `SYSTEM_PULLREQUEST_PULLREQUESTID` | Azure Pipelines automatic |
| `BUILD_REPOSITORY_ID` | Azure Pipelines automatic |
| `SYSTEM_TEAMPROJECT` | Azure Pipelines automatic |
| `SYSTEM_TEAMFOUNDATIONCOLLECTIONURI` | Azure Pipelines automatic |

### Additional variables for `pr-comment --platform github`

| Variable | Source |
|---|---|
| `GH_TOKEN` | Pass `${{ secrets.GITHUB_TOKEN }}` |
| `GITHUB_REPOSITORY` | GitHub Actions automatic |
| `GITHUB_EVENT_NAME` | GitHub Actions automatic |
| `GITHUB_REF` | GitHub Actions automatic |

---

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success / gate passed |
| 1 | User error (bad config, auth failure) |
| 2 | Transient error (network, API 5xx after retries) |
| 3 | Build gate blocked — blocking findings detected |

---

## Versioning

Tags follow semver: `vMAJOR`, `vMAJOR.MINOR`, `vMAJOR.MINOR.PATCH`, `latest`.

| Change | Version bump |
|---|---|
| Breaking API or behaviour change | Major |
| New scanner, new subcommand, new env var | Minor |
| Bug fix, dependency update | Patch |

Pin to `v1` in pipelines to auto-receive minor/patch updates. Pin to `v1.0.0` for strict reproducibility.

---

## SecureObs dashboard

[https://secureobs-dashboard.azurewebsites.net](https://secureobs-dashboard.azurewebsites.net)
