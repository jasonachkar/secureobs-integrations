#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(cat "$SCRIPT_DIR/VERSION" | tr -d '[:space:]')"

IFS='.' read -r MAJOR MINOR PATCH <<< "$VERSION"

IMAGE="secureobs/scanner"

echo "Building $IMAGE:$VERSION for linux/amd64..."

# Ensure buildx builder exists
if ! docker buildx inspect secureobs-builder >/dev/null 2>&1; then
    echo "Creating buildx builder..."
    docker buildx create --name secureobs-builder --use
    docker buildx inspect --bootstrap
else
    docker buildx use secureobs-builder
fi

# Build and push multi-platform image with all tags
docker buildx build \
    --platform linux/amd64 \
    --tag "$IMAGE:v${MAJOR}.${MINOR}.${PATCH}" \
    --tag "$IMAGE:v${MAJOR}.${MINOR}" \
    --tag "$IMAGE:v${MAJOR}" \
    --tag "$IMAGE:latest" \
    --push \
    "$SCRIPT_DIR"

echo "Done. Published $IMAGE at v${MAJOR}.${MINOR}.${PATCH}, v${MAJOR}.${MINOR}, v${MAJOR}, latest."
