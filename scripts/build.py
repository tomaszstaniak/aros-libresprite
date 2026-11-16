#!/usr/bin/env python3
"""Configure and build LibreSprite for AROS from work/libresprite.

    python3 scripts/build.py <target> [--configure-only] [-j N]

Needs the libraries from scripts/deps.py and the aros-sdl kit (local.json
"sdl_kit"). Output: build/<target>/ls (CMake tree) and the executable
build/<target>/ls/bin/libresprite. The log is build/<target>/build.log.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deps  # noqa: E402

ROOT = deps.ROOT


def build_host_gen(log):
    """LibreSprite's gen code generator runs on the build machine: build it with
    the host compiler (GEN_ONLY) and the bundled tinyxml2."""
    hb = ROOT / "build/host-gen"
    src = ROOT / "work/libresprite"
    lib = hb / "libtinyxml2-host.a"
    hb.mkdir(parents=True, exist_ok=True)
    deps.run(["c++", "-O2", "-std=c++17", "-c", src / "third_party/tinyxml2/tinyxml2.cpp",
              "-o", hb / "tinyxml2.o"], logfile=log)
    lib.unlink(missing_ok=True)
    deps.run(["ar", "rcs", lib, hb / "tinyxml2.o"], logfile=log)
    deps.run(["cmake", "-S", src, "-B", hb / "cmake", "-G", "Unix Makefiles", "-DGEN_ONLY=ON",
              "-DCMAKE_BUILD_TYPE=Release", f"-DTINYXML2_INCLUDE_DIR={src}/third_party/tinyxml2",
              f"-DTINYXML2_LIBRARY={lib}"], logfile=log)
    deps.run(["cmake", "--build", hb / "cmake", "--target", "gen", "-j", "8"], logfile=log)
    return hb / "cmake/bin/gen"


def check_cxxrt(cxxrt):
    """Every archive of the C++ runtime must match its BUILDINFO.txt."""
    import hashlib
    info = (cxxrt / "BUILDINFO.txt").read_text()
    for line in info.splitlines():
        if line.startswith("archive "):
            _, sha, name = line.split()
            got = hashlib.sha256((cxxrt / "lib" / name).read_bytes()).hexdigest()
            if got != sha:
                raise SystemExit(f"{name}: sha256 {got}, BUILDINFO says {sha}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=list(deps.ARCH_CFLAGS))
    ap.add_argument("--configure-only", action="store_true")
    ap.add_argument("-j", default="8")
    a = ap.parse_args()
    t = deps.config(a.target)
    base = ROOT / "build" / a.target
    d, kit, sdk = base / "deps", Path(t["sdl_kit"]), Path(t["sdk"])
    if not (d / "BUILD.json").exists():
        raise SystemExit("run scripts/deps.py first")
    bld = base / "ls"
    log = base / "build.log"
    log.unlink(missing_ok=True)
    gen = build_host_gen(log)
    opts = [
        f"-DCMAKE_TOOLCHAIN_FILE={ROOT}/cmake/aros.cmake", "-DCMAKE_BUILD_TYPE=Release",
        f"-DAROS_CC={t['cc']}", f"-DAROS_CXX={t['cxx']}", f"-DAROS_AR={t['ar']}", f"-DAROS_SDK={sdk}",
        "-DAROS_CFLAGS=" + " ".join(deps.ARCH_CFLAGS[a.target]),
        "-DCMAKE_POSITION_INDEPENDENT_CODE=OFF",
        "-DUSE_SDL2_BACKEND=OFF", "-DUSE_SDL3_BACKEND=ON",
        f"-DSDL3_DIR={kit}/lib/cmake/SDL3", f"-DSDL3_image_DIR={kit}/lib/cmake/SDL3_image",
        f"-DLibArchive_INCLUDE_DIR={d}/include", f"-DLibArchive_LIBRARY={d}/lib/libarchive.a",
        f"-DGIF_INCLUDE_DIR={d}/include", f"-DGIF_LIBRARY={d}/lib/libgif.a",
        f"-DPIXMAN_INCLUDE_DIR={d}/include/pixman-1", f"-DPIXMAN_LIBRARY={d}/lib/libpixman-1.a",
        f"-DTINYXML2_INCLUDE_DIR={d}/include", f"-DTINYXML2_LIBRARY={d}/lib/libtinyxml2.a",
        f"-DFREETYPE_LIBRARY={sdk}/lib/libfreetype2.static.a",
        f"-DICONV_INCLUDE_DIR={kit}/include", f"-DICONV_LIBRARY={kit}/lib/libiconv.a",
        f"-DGEN_EXECUTABLE={gen}",
    ]
    if t.get("cxxrt"):
        # Toolchains without a C++ standard library (Raspberry Pi, Clang 20):
        # libc++, libc++abi and libunwind built for the target ("cxxrt" in
        # local.json, a build-cxx-runtime.sh output checked by its BUILDINFO).
        cxxrt = Path(t["cxxrt"])
        check_cxxrt(cxxrt)
        opts += [f"-DCMAKE_CXX_FLAGS=-nostdinc++ -isystem {cxxrt}/include/c++/v1",
                 f"-DCMAKE_EXE_LINKER_FLAGS=-L{cxxrt}/lib"]
    fix = d / "lib/unwind-dw2-fixed.o"
    if fix.exists():
        # Linked ahead of libgcc (the driver adds -lgcc after these): C++ throws work.
        opts.append(f"-DCMAKE_CXX_STANDARD_LIBRARIES={fix}")
    deps.run(["cmake", "-S", ROOT / "work/libresprite", "-B", bld, "-G", "Unix Makefiles"] + opts, logfile=log)
    if a.configure_only:
        return
    deps.run(["cmake", "--build", bld, "-j", a.j, "--", "-k"], logfile=log)
    print(f"built: {bld}")


if __name__ == "__main__":
    main()
