---
type: guide
updated: 2026-11-16
---

# Reproducing and saving changes

Requirements: Git, bash, Python 3, tar, shasum.

## Sources

`upstreams.json` pins LibreSprite master at `89ea7597ed1d779e85c0019555f5b97c7eac22f0` (2026-11-14, after release 1.3; it has the SDL3 backend). Fetch it with its submodules:

```sh
git clone https://github.com/LibreSprite/LibreSprite.git upstream/libresprite
git -C upstream/libresprite checkout 89ea7597ed1d779e85c0019555f5b97c7eac22f0
git -C upstream/libresprite submodule update --init --recursive
```

Never edit `upstream/libresprite`.

## Work copy

```sh
scripts/bootstrap.sh
```

This creates `work/libresprite`: a Git repository whose first commit is the pinned
tree, with the submodules (`src/flic`, `third_party/simpleini`) as plain files, and one
commit per patch in `patches/libresprite/series`. Run again to confirm it still matches.
After the pin or series changes, `scripts/bootstrap.sh --recreate` builds a new copy and
moves the old one aside as `work/libresprite.old-<time>`; it refuses while there are
unsaved files.

## Saving a change

Edit files in `work/libresprite`, then:

```sh
scripts/save-patch.sh short-name "Title" [path ...]
```

Without paths every change is saved. The patch is written as the next number, added to
`series` and committed in the work copy. Fill in the header (problem, change, targets,
upstream status, verification, removal condition), then commit the patch and `series`
in this repository.

## Checking reproduction

```sh
scripts/check-reproduction.sh
```

Rebuilds pin + series in a temporary directory and compares it with the work copy's
last commit. Uncommitted changes are listed separately. Nothing in `upstream/` or `work/`
is changed.

The series is currently empty.
