#!/usr/bin/env python3
"""Build the libraries LibreSprite needs that the AROS SDKs do not have.

    python3 scripts/deps.py <target>

giflib and libarchive (zip reading only, for extensions) from release archives,
and pixman and tinyxml2 from LibreSprite's own third_party sources (the work copy),
static, into build/<target>/deps. SDL3 and SDL3_image come from the aros-sdl kit
(local.json "sdl_kit"). Compilers and SDKs come from local.json; AROS_CC,
AROS_CXX, AROS_AR and AROS_SDK override them.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = json.loads((ROOT / "upstreams.json").read_text())
DISTFILES = ROOT / "distfiles"
ARCH_CFLAGS = {
    "aros-x86_64-abiv1-pc": ["-m64", "-mcmodel=large", "-mno-red-zone", "-mno-ms-bitfields"],
    "aros-x86_64-abiv11-pc": ["-m64", "-mcmodel=large", "-mno-red-zone", "-mno-ms-bitfields"],
    "aros-aarch64-abiv1-raspi": [],
}
COMMON_CFLAGS = ["-O2", "-fno-asynchronous-unwind-tables", "-fno-omit-frame-pointer"]


def run(cmd, cwd=None, logfile=None, env=None):
    cmd = [str(c) for c in cmd]
    out = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if logfile:
        with open(logfile, "a") as f:
            f.write("$ " + " ".join(cmd) + "\n" + out.stdout + out.stderr)
    if out.returncode:
        sys.stderr.write(out.stdout[-3000:] + out.stderr[-3000:])
        raise SystemExit(f"failed ({out.returncode}): {' '.join(cmd)[:200]}")
    return out.stdout


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def config(target):
    local = ROOT / "local.json"
    cfg = json.loads(local.read_text()).get(target, {}) if local.exists() else {}
    t = {k: os.environ.get("AROS_" + k.upper(), cfg.get(k, "")) for k in ("cc", "cxx", "ar", "sdk", "sdl_kit")}
    for k, v in t.items():
        if not v or not Path(v).exists():
            raise SystemExit(f"{target}: '{k}' not set or missing ({v!r}); see local.example.json")
    # optional: C++ runtime for toolchains without one (see build.py)
    cxxrt = os.environ.get("AROS_CXXRT", cfg.get("cxxrt", ""))
    if cxxrt:
        if not (Path(cxxrt) / "BUILDINFO.txt").exists():
            raise SystemExit(f"{target}: 'cxxrt' {cxxrt!r} has no BUILDINFO.txt")
        t["cxxrt"] = cxxrt
    t["cflags"] = ARCH_CFLAGS[target] + COMMON_CFLAGS
    return t


def distfile(key):
    d = MANIFEST["distfiles"][key]
    p = DISTFILES / d["file"]
    if not p.exists():
        DISTFILES.mkdir(exist_ok=True)
        run(["curl", "-sSLf", "-L", "-o", p, d["url"]])
    if sha256(p) != d["sha256"]:
        raise SystemExit(f"{p}: SHA-256 differs from upstreams.json")
    return p


def series(repo):
    s = ROOT / "patches" / repo / "series"
    names = [l.split("#")[0].strip() for l in s.read_text().splitlines()]
    return [ROOT / "patches" / repo / n for n in names if n]


def unpack(archive, dest, patches):
    top = dest / archive.name[: -len(".tar.gz")]
    shutil.rmtree(top, ignore_errors=True)
    with tarfile.open(archive) as t:
        t.extractall(dest, filter="data")
    for p in patches:
        run(["patch", "-p1", "-s", "-N", "-i", p], cwd=top)
    return top


def check_no_got(t, lib):
    rel = run([t["ar"][:-2] + "readelf", "-r", "-W", lib])
    n = len(re.findall(r"R_X86_64_(?:GOT\w*|PLTOFF64)|R_AARCH64_\w*GOT\w*", rel))
    if n:
        raise SystemExit(f"{lib}: {n} GOT relocations (PIC code), AROS cannot load these")


def build_giflib(t, work, out, logfile):
    src = unpack(distfile("giflib"), work, series("giflib"))
    obj = work / "giflib-obj"
    shutil.rmtree(obj, ignore_errors=True)
    obj.mkdir()
    files = ["dgif_lib", "egif_lib", "gifalloc", "gif_err", "gif_font", "gif_hash", "openbsd-reallocarray"]
    objs = []
    for f in files:
        o = obj / (f + ".o")
        run([t["cc"], "--sysroot=" + t["sdk"]] + t["cflags"] + ["-std=gnu99", "-Wall",
             "-Werror=implicit-function-declaration", f"-ffile-prefix-map={work}=/deps",
             "-c", src / (f + ".c"), "-o", o], logfile=logfile)
        objs.append(o)
    lib = out / "lib/libgif.a"
    lib.unlink(missing_ok=True)
    run([t["ar"], "rcsD", lib] + objs, logfile=logfile)
    shutil.copy(src / "gif_lib.h", out / "include/gif_lib.h")
    shutil.copy(src / "COPYING", out / "licenses/giflib-COPYING")
    return lib


LS = ROOT / "work/libresprite"


def compile_all(t, compiler, srcs, objdir, flags, logfile):
    objdir.mkdir(parents=True, exist_ok=True)
    objs = []
    for s in srcs:
        o = objdir / (s.stem + ".o")
        run([compiler, "--sysroot=" + t["sdk"]] + t["cflags"] + flags + ["-c", s, "-o", o], logfile=logfile)
        objs.append(o)
    return objs


def build_pixman(t, work, out, logfile):
    """LibreSprite's bundled pixman (third_party/pixman), generic C paths only.
    No TLS on AROS: per-thread data through pthread keys (HAVE_PTHREADS, no TLS)."""
    src = LS / "third_party/pixman"
    cm = (src / "CMakeLists.txt").read_text()
    files = re.findall(r"^\s*(pixman/pixman[\w-]*\.c)\s*\)?\s*$", cm.split("set(PIXMAN_CFLAGS")[0], re.M)
    gen = work / "pixman-gen"
    gen.mkdir(parents=True, exist_ok=True)
    (gen / "pixman-config.h").write_text("")
    ver = re.search(r'CONTENT "\n(#pragma once.*?)"\)', cm, re.S).group(1).replace('\\"', '"')
    (gen / "pixman-version.h").write_text(ver)
    flags = ["-std=gnu99", "-DHAVE_BUILTIN_CLZ=1", "-DHAVE_PTHREADS=1", '-DPACKAGE="pixman"',
             "-DSIZEOF_LONG=8", "-Werror=implicit-function-declaration",
             f"-I{src}/pixman", f"-I{gen}", f"-ffile-prefix-map={LS}=/libresprite"]
    objs = compile_all(t, t["cc"], [src / f for f in files], work / "pixman-obj", flags, logfile)
    lib = out / "lib/libpixman-1.a"
    lib.unlink(missing_ok=True)
    run([t["ar"], "rcsD", lib] + objs, logfile=logfile)
    (out / "include/pixman-1").mkdir(exist_ok=True)
    shutil.copy(src / "pixman/pixman.h", out / "include/pixman-1/pixman.h")
    shutil.copy(gen / "pixman-version.h", out / "include/pixman-1/pixman-version.h")
    shutil.copy(src / "COPYING", out / "licenses/pixman-COPYING")
    return lib


def build_tinyxml2(t, work, out, logfile):
    """LibreSprite's bundled tinyxml2 (third_party/tinyxml2)."""
    src = LS / "third_party/tinyxml2"
    objs = compile_all(t, t["cxx"], [src / "tinyxml2.cpp"], work / "tinyxml2-obj",
                       ["-std=c++17", f"-ffile-prefix-map={LS}=/libresprite"], logfile)
    lib = out / "lib/libtinyxml2.a"
    lib.unlink(missing_ok=True)
    run([t["ar"], "rcsD", lib] + objs, logfile=logfile)
    shutil.copy(src / "tinyxml2.h", out / "include/tinyxml2.h")
    shutil.copy(src / "LICENSE.txt", out / "licenses/tinyxml2-LICENSE.txt")
    return lib


def build_libarchive(t, work, out, logfile):
    src = unpack(distfile("libarchive"), work, series("libarchive"))
    bld = work / "libarchive-build"
    shutil.rmtree(bld, ignore_errors=True)
    off = ["OPENSSL", "LIBXML2", "EXPAT", "LZMA", "ZSTD", "LZ4", "BZip2", "LIBB2", "ICONV",
           "ACL", "XATTR", "CNG", "MBEDTLS", "NETTLE", "LZO", "PCREPOSIX", "PCRE2POSIX",
           "WIN32_XMLLITE", "TAR", "CPIO", "CAT", "UNZIP", "TEST", "COVERAGE"]
    opts = [f"-DENABLE_{o}=OFF" for o in off] + [
        "-DENABLE_ZLIB=ON", "-DENABLE_INSTALL=ON", "-DBUILD_SHARED_LIBS=OFF",
        "-DCMAKE_POSITION_INDEPENDENT_CODE=OFF"]
    cflags = " ".join(t["cflags"] + [f"-ffile-prefix-map={work}=/deps"])
    run(["cmake", "-S", src, "-B", bld, "-G", "Unix Makefiles",
         f"-DCMAKE_TOOLCHAIN_FILE={ROOT}/cmake/aros.cmake", "-DCMAKE_BUILD_TYPE=Release",
         f"-DAROS_CC={t['cc']}", f"-DAROS_AR={t['ar']}", f"-DAROS_SDK={t['sdk']}",
         f"-DAROS_CFLAGS={cflags}", f"-DCMAKE_INSTALL_PREFIX={out}"] + opts, logfile=logfile)
    run(["cmake", "--build", bld, "-j8", "--target", "archive_static"], logfile=logfile)
    shutil.copy(bld / "libarchive/libarchive.a", out / "lib/libarchive.a")
    for h in ("archive.h", "archive_entry.h"):
        shutil.copy(src / "libarchive" / h, out / "include" / h)
    shutil.copy(src / "COPYING", out / "licenses/libarchive-COPYING")
    return out / "lib/libarchive.a"


def build_unwind_fix(t, work, out, logfile, variant="fixed"):
    """Mainline x86_64 GCC 10.5 toolchains built before AROS 52bab89955 have a
    libgcc unwinder without its register size table: every C++ throw aborts.
    Rebuild libgcc's own unwind-dw2.c without the AROS guard around
    __builtin_init_dwarf_reg_size_table (AROS-dev platform note
    v1-unwinder-register-table-20261103). Needs the configured GCC build tree
    ("gcc_build" in local.json). variant="stock" rebuilds the unchanged source,
    to compare it with the toolchain's object."""
    cfg = json.loads((ROOT / "local.json").read_text())[TARGET]
    g0 = Path(cfg["gcc_build"])
    g = g0 / "gen/host/tools/crosstools/gnu/gcc"
    p = g0 / "Ports/host/gcc/gcc-10.5.0/libgcc"
    tc = Path(t["cc"]).parent
    d = work / ("unwind-" + variant)
    d.mkdir(parents=True, exist_ok=True)
    src = (p / "unwind-dw2.c").read_text()
    if variant == "fixed":
        guarded = ("#ifdef MD_FALLBACK_FRAME_STATE_FOR\n"
                   "  __builtin_init_dwarf_reg_size_table (dwarf_reg_size_table);\n#endif\n")
        if guarded not in src:
            raise SystemExit("unwind-dw2.c: AROS guard not found; is this toolchain already fixed?")
        src = src.replace(guarded, "  __builtin_init_dwarf_reg_size_table (dwarf_reg_size_table);\n")
    (d / "unwind-dw2.c").write_text(src)
    run([g / "gcc/xgcc", f"-B{g}/gcc/", f"-B{tc}/x86_64-aros/bin/", f"-B{tc}/x86_64-aros/lib/",
         "-isystem", f"{tc}/x86_64-aros/include", "-isystem", f"{tc}/x86_64-aros/sys-include",
         "-mcmodel=large", "-O2", "-DIN_GCC", "-DCROSS_DIRECTORY_STRUCTURE", "-isystem", "./include",
         "-DIN_LIBGCC2", "-fbuilding-libgcc", "-fno-stack-protector", "-I.", "-I../.././gcc",
         f"-I{p}", f"-I{p}/../gcc", f"-I{p}/../include", "-fexceptions", "-fvisibility=hidden",
         "-DHIDE_EXPORTS", "-c", d / "unwind-dw2.c", "-o", d / "unwind-dw2.o"],
        cwd=g / "x86_64-aros/libgcc", logfile=logfile)
    obj = d / "unwind-dw2.o"
    if variant == "fixed":
        if not re.search(r" dwarf_reg_size_table$", run([t["ar"][:-2] + "nm", obj]), re.M):
            raise SystemExit("unwind fix not effective: no dwarf_reg_size_table")
        shutil.copy(obj, out / "lib/unwind-dw2-fixed.o")
        return out / "lib/unwind-dw2-fixed.o"
    return obj


TARGET = None


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ARCH_CFLAGS:
        raise SystemExit("usage: deps.py " + "|".join(ARCH_CFLAGS))
    global TARGET
    target = TARGET = sys.argv[1]
    t = config(target)
    base = ROOT / "build" / target
    work, out = base / "deps-work", base / "deps"
    shutil.rmtree(out, ignore_errors=True)
    for d in (work, out / "lib", out / "include", out / "licenses"):
        d.mkdir(parents=True, exist_ok=True)
    logfile = base / "deps.log"
    logfile.unlink(missing_ok=True)
    info = {"target": target, "compiler": run([t["cc"], "--version"]).splitlines()[0], "parts": {}}
    if not (LS / ".git/aros-inputs").exists():
        raise SystemExit("work/libresprite missing; run scripts/bootstrap.sh")
    for name, fn in (("giflib", build_giflib), ("libarchive", build_libarchive),
                     ("pixman", build_pixman), ("tinyxml2", build_tinyxml2)):
        print(f"{target}: {name}", flush=True)
        lib = fn(t, work, out, logfile)
        check_no_got(t, lib)
        if name in MANIFEST["distfiles"]:
            d = MANIFEST["distfiles"][name]
            info["parts"][name] = {"source": d["file"], "sha256": d["sha256"],
                                   "patches": [p.name for p in series(name)], "library_sha256": sha256(lib)}
        else:
            info["parts"][name] = {"source": "work/libresprite/third_party/" + name,
                                   "library_sha256": sha256(lib)}
    if target == "aros-x86_64-abiv1-pc":
        print(f"{target}: unwind fix", flush=True)
        stock = build_unwind_fix(t, work, out, logfile, "stock")
        orig = work / "unwind-orig"
        orig.mkdir(exist_ok=True)
        run([t["ar"], "x", run([t["cc"], "-print-libgcc-file-name"]).strip(), "unwind-dw2.o"], cwd=orig)
        dis = lambda o: re.sub(r"^.*file format.*$", "", run([t["ar"][:-2] + "objdump", "-d", "-r", o]), flags=re.M)
        if dis(stock) != dis(orig / "unwind-dw2.o"):
            raise SystemExit("rebuilt stock unwind-dw2.o differs from the toolchain's: recipe mismatch")
        fixed = build_unwind_fix(t, work, out, logfile)
        info["parts"]["unwind-fix"] = {"source": "toolchain GCC build tree libgcc/unwind-dw2.c, AROS guard removed",
                                       "stock_rebuild_matches": True, "object_sha256": sha256(fixed)}
    (out / "BUILD.json").write_text(json.dumps(info, indent=2) + "\n")
    print(f"deps: {out}")


if __name__ == "__main__":
    main()
