#!/bin/sh
# Builds the Workbench tool icon LibreSprite.info and the drawer icon drawer.info with the AROS icon tool
# ilbmtoicon (AROS PNG icon with a normal and a selected image) from
# LibreSprite's 64x64 application icon; the selected image is darker.
#   ILBMTOICON  ilbmtoicon from an AROS build tree (bin/<host>/tools)
# Needs netpbm (pngtopam, pamfunc, pamtopng). Output: build/icon/LibreSprite.info
set -eu
: "${ILBMTOICON:?Set ILBMTOICON to the AROS ilbmtoicon tool}"
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
png="$repo/work/libresprite/desktop/icons/hicolor/64x64/apps/libresprite.png"
out="$repo/build/icon"
mkdir -p "$out"
cp "$png" "$out/LibreSprite.png"
pngtopam -alphapam "$png" | pamfunc -multiplier=0.7 | pamtopng > "$out/LibreSprite-selected.png"
"$ILBMTOICON" "$repo/assets/icon/LibreSprite.info.src" "$out/LibreSprite.png" "$out/LibreSprite-selected.png" "$out/LibreSprite.info"
"$ILBMTOICON" "$repo/assets/icon/drawer.info.src" "$out/LibreSprite.png" "$out/LibreSprite-selected.png" "$out/drawer.info"
(cd "$out" && shasum -a 256 LibreSprite.info drawer.info)
