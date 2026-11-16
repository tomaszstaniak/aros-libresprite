---
type: guide
updated: 2026-11-16
---

# Development

## Supported scope

Targets: x86_64 ABIv11 distributions (`aros-x86_64-abiv11-pc`), mainline AROS x86_64
(`aros-x86_64-abiv1-pc`) and mainline AROS on the Raspberry Pi (`aros-aarch64-abiv1-raspi`).
All three build from the same patch series.

## Prerequisites

- An AROS cross toolchain and Developer SDK for the target: GCC 10.5 for both x86_64
  targets, the Clang 20 Raspberry Pi toolchain for the Pi.
- The [aros-sdl](https://github.com/tomaszstaniak/aros-sdl) kit for the same target
  (SDL3, SDL3_image and libiconv).
- On the build machine: CMake 4.1 or later, a C++ compiler, Python 3, Git.
- Mainline x86_64 toolchains built before AROS commit 52bab89955 cannot catch C++
  exceptions; `scripts/deps.py` then rebuilds libgcc's unwinder object from the
  toolchain's GCC build tree (`gcc_build` in `local.json`).
- The Raspberry Pi toolchain has no C++ standard library. Point `cxxrt` in `local.json`
  at a build of libc++, libc++abi and libunwind 20.1.0 for that target with its
  `BUILDINFO.txt`; `scripts/build.py` checks the archives against it.

Copy `local.example.json` to `local.json` and fill in the paths.

## Build

    scripts/bootstrap.sh                       # work/libresprite from the pin and patches
    python3 scripts/deps.py <target>           # giflib, libarchive, pixman, tinyxml2
    python3 scripts/build.py <target>          # LibreSprite itself

The program is `build/<target>/ls/bin/libresprite` with its `data` drawer beside it.
`gen`, LibreSprite's code generator, is built for the build machine first
(`build/host-gen`).

## Package

    ILBMTOICON=<AROS build>/tools/ilbmtoicon sh scripts/make-icon.sh
    python3 scripts/make-drawer.py <target> 1.3.99.20261114-aros3
    APKG_PACK=<apkg-pack.pyz> scripts/package.sh 1.3.99.20261114-aros3

`make-drawer.py` assembles the drawer (program without unneeded symbols, icons, `data`,
`ReadMe.txt`, licences) and the apkg description, with the system libraries the program
opens at start-up read from the build. `package.sh` checks and packs each drawer with
apkg-pack and writes `dist/<release>/` with `SHA256SUMS`.

## Not available on AROS yet

- Scripts' `fetch()` and `HTTPServer` report that they are not available.
- Starting external programs from scripts.
