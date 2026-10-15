#!/usr/bin/env bash
# Upload processed books to R2 storage using an existing AWS CLI profile.
set -euo pipefail

if [[ $# -lt 3 || $# -gt 4 ]]; then
  echo 'Usage: bash scripts/upload-books.sh BUCKET ENDPOINT SOURCE_DIR [--upload]' >&2
  echo 'Default: preview only. Set R2_PROFILE to choose a profile (default: r2).' >&2
  exit 2
fi

bucket=$1
endpoint=$2
source_dir=$3
mode=${4:-}
profile=${R2_PROFILE:-r2}

if [[ ! "$bucket" =~ ^[a-z0-9][a-z0-9.-]*[a-z0-9]$ ]]; then
  echo 'Supply a bucket name, without s3:// or a path.' >&2
  exit 2
fi
if [[ ! "$endpoint" =~ ^https://[a-zA-Z0-9.-]+\.r2\.cloudflarestorage\.com/?$ ]]; then
  echo 'Supply the HTTPS S3 API endpoint copied from your R2 bucket overview.' >&2
  exit 2
fi
if [[ ! -d "$source_dir" || ( -n "$mode" && "$mode" != --upload ) ]]; then
  echo 'Source must be a directory; the optional fourth argument is --upload.' >&2
  exit 2
fi
command -v aws >/dev/null || { echo 'Install AWS CLI first.' >&2; exit 1; }

options=(--dryrun)
if [[ "$mode" == --upload ]]; then
  options=(--no-progress --only-show-errors)
fi

# No remote deletions. Symlinks are skipped so the upload stays within the source.
# AWS compares size and modification time; changed files replace matching keys.
aws --profile "$profile" --region auto --endpoint-url "$endpoint" \
  s3 sync "${source_dir%/}/" "s3://$bucket/" \
  --no-follow-symlinks "${options[@]}"
