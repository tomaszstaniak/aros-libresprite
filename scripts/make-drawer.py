#!/usr/bin/env python3
"""Prepare the LibreSprite drawer and its package description for one target.

    python3 scripts/make-drawer.py <target> <release>     e.g. 1.3.99.20261114-aros1

Reads the build of scripts/build.py (build/<target>/ls/bin), the icons of
scripts/make-icon.sh (build/icon) and packaging/. Writes
build/<target>/drawer/LibreSprite (the drawer), LibreSprite.info (its
icon) and LibreSprite.arospkg.toml beside it, for apkg-pack (scripts/package.sh).
The program is stripped of symbols it does not need.
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deps  # noqa: E402

ROOT = deps.ROOT
WORK = ROOT / "work/libresprite"

# Libraries the program opens at start-up (__aros_libreq_* without a weak
# fallback, read from each build): checked per target, never copied across.
COMMON_LIBS = ["commodities.library", "cybergraphics.library", "datatypes.library",
               "gadtools.library", "icon.library", "iffparse.library", "jfif.library",
               "keymap.library", "png.library", "workbench.library", "z1.library"]
TARGETS = {
    "aros-x86_64-abiv1-pc": ("x86_64", "v1", ["posixc.library", "stdc.library", "stdcio.library"]),
    "aros-aarch64-abiv1-raspi": ("aarch64", "v1", ["posixc.library", "stdc.library", "stdcio.library"]),
    # ABIv11: C library and libGL link stubs open these.
    "aros-x86_64-abiv11-pc": ("x86_64", "v11", ["crt.library", "stdlib.library", "m.library", "gl.library"]),
}
LIB_BASES = {"CxBase": "commodities.library", "CyberGfxBase": "cybergraphics.library",
             "DataTypesBase": "datatypes.library", "GadToolsBase": "gadtools.library",
             "IconBase": "icon.library", "IFFParseBase": "iffparse.library",
             "JpegBase": "jfif.library", "KeymapBase": "keymap.library", "PngBase": "png.library",
             "WorkbenchBase": "workbench.library", "Z1Base": "z1.library",
             "PosixCBase": "posixc.library", "StdCBase": "stdc.library", "StdCIOBase": "stdcio.library",
             "CrtBase": "crt.library", "StdlibBase": "stdlib.library", "MBase": "m.library",
             "GLBase": "gl.library"}
CORE_BASES = {"SysBase", "DOSBase", "GfxBase", "IntuitionBase"}


def tool(t, name):
    """A binutils tool beside the target compiler (llvm-* for the Pi)."""
    cc = Path(t["cc"])
    for cand in (cc.with_name(cc.name.replace("gcc", name)),
                 cc.parent.parent / "libexec/llvm/bin" / f"llvm-{name}"):
        if cand.exists():
            return str(cand)
    raise SystemExit(f"no {name} for {cc}")


def required_libraries(t, binary):
    """Bases the program opens at start-up: defined __aros_libreq_<Base>
    symbols (not the weak version markers)."""
    out = subprocess.run([tool(t, "nm"), binary], capture_output=True, text=True, check=True).stdout
    found = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 2 or not parts[-1].startswith("__aros_libreq_"):
            continue
        kind, name = parts[-2], parts[-1][len("__aros_libreq_"):]
        if kind in ("W", "w") or "." in name:
            continue
        found.add(name)
    unknown = found - set(LIB_BASES) - CORE_BASES
    if unknown:
        raise SystemExit(f"unknown library bases {sorted(unknown)}: add them to LIB_BASES")
    libs = sorted(LIB_BASES[b] for b in found if b in LIB_BASES)
    # The base name does not always give the library name (JpegBase opens
    # jfif.library): every name must be the one the program opens.
    names = set(re.findall(rb"[a-z0-9_.]+\.library", Path(binary).read_bytes()))
    absent = [l for l in libs if l.encode() not in names]
    if absent:
        raise SystemExit(f"library names not found in the program: {absent}: fix LIB_BASES")
    return libs


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    target, release = sys.argv[1], sys.argv[2]
    m = re.fullmatch(r"([0-9.]+)-aros([0-9]+)", release)
    if not m or target not in TARGETS:
        raise SystemExit("usage: make-drawer.py <target> <version>-aros<revision>")
    version, revision = m.group(1), int(m.group(2))
    arch, abi, runtime = TARGETS[target]
    t = deps.config(target)
    built = ROOT / "build" / target / "ls/bin"
    icons = ROOT / "build/icon"
    for p in (built / "libresprite", built / "data", icons / "LibreSprite.info", icons / "drawer.info"):
        if not p.exists():
            raise SystemExit(f"missing {p}")

    stage = ROOT / "build" / target / "drawer"
    if stage.exists():
        shutil.rmtree(stage)
    drawer = stage / "LibreSprite"
    drawer.mkdir(parents=True)

    program = drawer / "LibreSprite"
    shutil.copy2(built / "libresprite", program)
    unstripped = sha256(program)
    subprocess.run([tool(t, "strip"), "--strip-unneeded", "--remove-section", ".comment", program], check=True)
    shutil.copytree(built / "data", drawer / "data")
    shutil.copy2(icons / "LibreSprite.info", drawer / "LibreSprite.info")
    shutil.copy2(icons / "drawer.info", stage / "LibreSprite.info")
    shutil.copy2(ROOT / "packaging/ReadMe.txt", drawer / "ReadMe.txt")
    shutil.copy2(WORK / "LICENSE.txt", drawer / "LICENSE.txt")

    # Licences of everything linked into the program.
    lic = drawer / "Licenses"
    lic.mkdir()
    kit = Path(t["sdl_kit"]) / "licenses"
    depl = ROOT / "build" / target / "deps/licenses"
    texts = {
        "SDL3.txt": kit / "SDL3-LICENSE.txt",
        "SDL3_image.txt": kit / "SDL3_image-LICENSE.txt",
        "libiconv-LGPL-2.1.txt": kit / "libiconv-COPYING.LIB",
        "giflib.txt": depl / "giflib-COPYING",
        "libarchive.txt": depl / "libarchive-COPYING",
        "pixman.txt": depl / "pixman-COPYING",
        "tinyxml2.txt": depl / "tinyxml2-LICENSE.txt",
        "QuickJS.txt": WORK / "docs/licenses/quickjs-amalgam-LICENSE.txt",
        "delta.txt": WORK / "third_party/delta/LICENSE.txt",
        "simpleini.txt": WORK / "third_party/simpleini/LICENCE.txt",
        "modp_b64.txt": WORK / "third_party/modp_b64/LICENSE",
        "observable.txt": WORK / "third_party/observable/LICENSE.txt",
        "FreeType-FTL.txt": ROOT / "packaging/licenses/FreeType-FTL.txt",
    }
    if t.get("cxxrt"):
        texts["LLVM-runtime.txt"] = ROOT / "packaging/licenses/LLVM-LICENSE.txt"
    for name, src in texts.items():
        if not src.exists():
            raise SystemExit(f"missing licence text {src}")
        shutil.copy2(src, lic / name)
    notices = (ROOT / "packaging/NOTICES.txt").read_text()
    if t.get("cxxrt"):
        notices += ("\nLLVM libc++, libc++abi and libunwind 20.1.0 (Raspberry Pi build only):\n"
                    "  Apache License 2.0 with LLVM Exceptions, LLVM-runtime.txt\n")
    (lic / "NOTICES.txt").write_text(notices)

    libs = required_libraries(t, built / "libresprite")
    missing = set(runtime) - set(libs)
    if missing:
        raise SystemExit(f"{target}: expected runtime libraries not found in the program: {sorted(missing)}")

    pin = json.loads((ROOT / "upstreams.json").read_text())["repositories"]["libresprite"]["commit"]
    kit_info = json.loads((Path(t["sdl_kit"]) / "BUILD.json").read_text())
    manifest = {
        "schema": 1, "application": "LibreSprite", "version": version, "release": release,
        "target": target,
        "source": {"upstream": "https://github.com/LibreSprite/LibreSprite",
                   "upstream_commit": pin,
                   "work_revision": subprocess.run(["git", "-C", WORK, "rev-parse", "HEAD"],
                                                   capture_output=True, text=True, check=True).stdout.strip(),
                   "patches": sum(1 for l in (ROOT / "patches/libresprite/series").read_text().splitlines()
                                  if l.strip() and not l.startswith("#"))},
        "build": {"compiler": subprocess.run([t["cc"], "--version"], capture_output=True, text=True).stdout.splitlines()[0],
                  "sdl_kit": {"contrib": kit_info.get("contrib"), "parts": sorted(kit_info.get("parts", {}))},
                  "unstripped_sha256": unstripped, "binary_sha256": sha256(program),
                  "strip_flags": ["--strip-unneeded", "--remove-section", ".comment"]},
        "requires_system": libs,
    }
    (drawer / "BUILD-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")

    toml = (ROOT / "packaging/LibreSprite.arospkg.toml.in").read_text()
    toml = (toml.replace("@VERSION@", version).replace("@REVISION@", str(revision))
            .replace("@ARCH@", arch).replace("@ABI@", abi))
    if abi == "v1":  # mainline and Pi builds follow a nightly's SDK: name the oldest one
        note = (ROOT / "packaging/nightly-note.txt").read_text().strip()
        head = "post_install_notes = [\n"
        assert toml.count(head) == 1
        toml = toml.replace(head, head + f'  "{note}",\n')
    for lib in libs:
        toml += f'\n[[requires_system]]\ntype = "library"\nid = "{lib}"\n'
    toml += (f'\n[source]\nrepository = "https://github.com/tomaszstaniak/aros-libresprite"\n'
             f'revision = "v{release}"\n\n[launch]\nexecutable = "LibreSprite"\nmode = "workbench"\n')
    (stage / "LibreSprite.arospkg.toml").write_text(toml)
    print(f"drawer: {drawer}\nrequires: {', '.join(libs)}")


if __name__ == "__main__":
    main()
