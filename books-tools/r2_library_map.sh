#!/usr/bin/env bash
# Regenerate LIBRARY.md from the README.md/INDEX.md files that are published in R2, and optionally upload it.
#   bash tools/r2_library_map.sh [--upload]
# Uses the aws CLI profile "r2-books" (R2_PROFILE) (credentials stay in ~/.aws). Endpoint/bucket can be overridden by R2_ENDPOINT / R2_BUCKET.
# Books are stored only in R2, so the map is built from a temporary download of each book's README.md and INDEX.md.
set -euo pipefail
BUCKET=${R2_BUCKET:-brg-books}
ENDPOINT=${R2_ENDPOINT:-https://7a0d8a20a1daaaab0534f11839b6a552.r2.cloudflarestorage.com}
TOOLS=$(cd "$(dirname "$0")" && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
r2() { aws --profile "${R2_PROFILE:-r2-books}" --region auto --endpoint-url "$ENDPOINT" "$@"; }
for b in $(r2 s3 ls "s3://$BUCKET/" | awk '$1=="PRE"{print $2}' | tr -d /); do
  [ "$b" = RAW ] && continue
  r2 s3 cp "s3://$BUCKET/$b/README.md" "$TMP/$b/README.md" --only-show-errors 2>/dev/null || continue
  r2 s3 cp "s3://$BUCKET/$b/INDEX.md" "$TMP/$b/INDEX.md" --only-show-errors 2>/dev/null || true
done
r2 s3 cp "s3://$BUCKET/PROCESSED.md" "$TMP/PROCESSED.md" --only-show-errors 2>/dev/null || true
mkdir -p "$TMP/tools" && cp "$TOOLS/library_map.py" "$TMP/tools/"
(cd "$TMP" && python3 -I tools/library_map.py)
cp "$TMP/LIBRARY.md" "$TOOLS/../LIBRARY.md"
if [ "${1:-}" = --upload ]; then
  r2 s3 cp "$TMP/LIBRARY.md" "s3://$BUCKET/LIBRARY.md" --only-show-errors && echo "uploaded LIBRARY.md"
fi
