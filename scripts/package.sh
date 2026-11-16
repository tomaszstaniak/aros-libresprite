#!/bin/bash
# Pack the drawers of scripts/make-drawer.py into the release archives.
#
#   APKG_PACK=<apkg-pack.pyz> scripts/package.sh <version>-aros<revision>
#
# For each target with a prepared drawer: apkg-pack check (drawer), build,
# check (archive), then the archive is extracted again and compared with the
# drawer. Output: dist/<release>/libresprite-<release>-<target>.zip and
# dist/<release>/SHA256SUMS.
set -euo pipefail
: "${APKG_PACK:?Set APKG_PACK to apkg-pack.pyz}"
[ $# -eq 1 ] || { echo "usage: scripts/package.sh <version>-aros<revision>" >&2; exit 1; }
REL="$1"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/dist/$REL"
mkdir -p "$OUT"
for T in aros-x86_64-abiv11-pc aros-x86_64-abiv1-pc aros-aarch64-abiv1-raspi; do
  D="$ROOT/build/$T/drawer/LibreSprite"
  [ -d "$D" ] || { echo "package: no drawer for $T (scripts/make-drawer.py)" >&2; exit 1; }
  Z="$OUT/libresprite-$REL-$T.zip"
  [ -e "$Z" ] && { echo "package: $Z exists; a delivered archive is never replaced" >&2; exit 1; }
  python3 "$APKG_PACK" check "$D"
  python3 "$APKG_PACK" build "$D" --output "$Z"
  python3 "$APKG_PACK" check "$Z"
  TMP="$(mktemp -d "$ROOT/build/package.XXXXXX")"
  unzip -q "$Z" -d "$TMP"
  diff -qr -x application.json -x .arospkg "$D" "$TMP/LibreSprite"
  rm -rf "$TMP"
done
( cd "$OUT" && shasum -a 256 libresprite-*.zip > SHA256SUMS && cat SHA256SUMS )
