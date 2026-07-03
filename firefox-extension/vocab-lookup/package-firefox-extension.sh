#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIST_DIR="$ROOT_DIR/dist/firefox"

cd "$SCRIPT_DIR"

for required_file in manifest.json popup.html popup.css popup.js background.js content.js; do
  if [[ ! -f "$required_file" ]]; then
    echo "Missing required extension file: $required_file" >&2
    exit 1
  fi
done

if command -v node >/dev/null 2>&1; then
  node --check popup.js
  node --check background.js
  node --check content.js
else
  echo "node not found; skipping JavaScript syntax check."
fi

if ! command -v zip >/dev/null 2>&1; then
  echo "zip is required to package the extension." >&2
  exit 1
fi

VERSION="$(node -e "console.log(require('./manifest.json').version)" 2>/dev/null || sed -n 's/.*\"version\"[[:space:]]*:[[:space:]]*\"\\([^\"]*\\)\".*/\\1/p' manifest.json | head -1)"
PACKAGE_NAME="slss-vocabulary-lookup-${VERSION:-dev}.xpi"

mkdir -p "$DIST_DIR"
rm -f "$DIST_DIR/$PACKAGE_NAME"

zip -qr "$DIST_DIR/$PACKAGE_NAME" \
  manifest.json \
  popup.html \
  popup.css \
  popup.js \
  background.js \
  content.js \
  README.md

echo "Packaged Firefox extension:"
echo "$DIST_DIR/$PACKAGE_NAME"
