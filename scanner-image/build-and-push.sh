#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(cat "$SCRIPT_DIR/VERSION" | tr -d '[:space:]')"

IFS='.' read -r MAJOR MINOR PATCH <<< "$VERSION"

IMAGE="secureobs/scanner"

echo "Building $IMAGE:$VERSION"
docker build -t "$IMAGE:$VERSION" "$SCRIPT_DIR"

echo "Tagging..."
docker tag "$IMAGE:$VERSION" "$IMAGE:v${MAJOR}.${MINOR}.${PATCH}"
docker tag "$IMAGE:$VERSION" "$IMAGE:v${MAJOR}.${MINOR}"
docker tag "$IMAGE:$VERSION" "$IMAGE:v${MAJOR}"
docker tag "$IMAGE:$VERSION" "$IMAGE:latest"

echo "Pushing..."
docker push "$IMAGE:v${MAJOR}.${MINOR}.${PATCH}"
docker push "$IMAGE:v${MAJOR}.${MINOR}"
docker push "$IMAGE:v${MAJOR}"
docker push "$IMAGE:latest"

echo "Done. Published $IMAGE at v${MAJOR}.${MINOR}.${PATCH}, v${MAJOR}.${MINOR}, v${MAJOR}, latest."
