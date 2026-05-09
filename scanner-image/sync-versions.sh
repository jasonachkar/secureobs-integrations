#!/usr/bin/env bash
# sync-versions.sh — reads VERSION and updates every version constant in the
# codebase so nothing needs to be touched manually after bumping the VERSION file.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

VERSION="$(cat "$SCRIPT_DIR/VERSION" | tr -d '[:space:]')"
IFS='.' read -r MAJOR MINOR PATCH <<< "$VERSION"

CODE_TEMPLATES="$REPO_ROOT/SecureObs.Dashboard/src/app/core/utils/code-templates.ts"
FEATURES_TS="$REPO_ROOT/SecureObs.Dashboard/src/app/features/features/features.component.ts"

# Portable sed -i (macOS needs a backup extension, Linux doesn't care)
sedi() { sed -i.bak "$@" && rm -f "${@: -1}.bak"; }

echo "  Syncing versions → v${VERSION} (major: v${MAJOR})"

# ── code-templates.ts ────────────────────────────────────────────────────────
if [ -f "$CODE_TEMPLATES" ]; then
    sedi "s/^export const SCANNER_IMAGE_TAG  = 'v[0-9]*';$/export const SCANNER_IMAGE_TAG  = 'v${MAJOR}';/" "$CODE_TEMPLATES"
    sedi "s/^export const INTEGRATIONS_TAG   = 'v[^']*';$/export const INTEGRATIONS_TAG   = 'v${VERSION}';/" "$CODE_TEMPLATES"
    echo "  ✔ code-templates.ts  →  SCANNER_IMAGE_TAG=v${MAJOR}  INTEGRATIONS_TAG=v${VERSION}"
else
    echo "  ⚠ code-templates.ts not found — skipping"
fi

# ── features.component.ts ─────────────────────────────────────────────────────
if [ -f "$FEATURES_TS" ]; then
    sedi "s/refs\/tags\/v[0-9][0-9.]*/refs\/tags\/v${VERSION}/g"                                      "$FEATURES_TS"
    sedi "s/secureobs-integrations\/\.github\/workflows\/secureobs\.yml@v[0-9][0-9.]*/secureobs-integrations\/.github\/workflows\/secureobs.yml@v${VERSION}/g" "$FEATURES_TS"
    sedi "s/imageTag:  'v[0-9]*'/imageTag:  'v${MAJOR}'/g"                                            "$FEATURES_TS"
    sedi "s/image-tag:  v[0-9]*/image-tag:  v${MAJOR}/g"                                              "$FEATURES_TS"
    echo "  ✔ features.component.ts  →  integrations tag=v${VERSION}  image tag=v${MAJOR}"
else
    echo "  ⚠ features.component.ts not found — skipping"
fi

echo "  Version sync complete."
