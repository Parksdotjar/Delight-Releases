"""Build/verify native release packages and combine their verified platform manifests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "Parksdotjar/Delight-Releases"
BUNDLE_ID = "com.subscribetoparks.delight"
NOTICES = ["LICENSE-MIT", "LICENSE-APACHE", "NOTICE", "THIRD_PARTY_NOTICES.md", "UPSTREAM_ATTRIBUTION.md", "ATTRIBUTION.md"]


def run(*args):
    return subprocess.check_output([str(a) for a in args], text=True).strip()


def version():
    return tomllib.loads((ROOT / "Cargo.toml").read_text())["workspace"]["package"]["version"]


def stable(tag):
    if not re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag):
        raise ValueError("A stable vX.Y.Z tag is required")
    return tag[1:]


def asset(path, tag):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", path.name):
        raise ValueError("Invalid release filename")
    if not 64 <= path.stat().st_size <= 2 * 1024**3:
        raise ValueError("Release asset exceeds size limits")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"url": f"https://github.com/{REPOSITORY}/releases/download/{tag}/{path.name}", "sha256": digest, "size": path.stat().st_size}


def write_manifest(path, tag, platforms):
    path.write_text(json.dumps({"schema": 1, "version": stable(tag), "tag": tag, "notes": "", "platforms": platforms}, indent=2) + "\n")


def verify_mac(app, expected_version, architecture):
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    assert info["CFBundleIdentifier"] == BUNDLE_ID, "Incorrect bundle identifier"
    assert info["CFBundleExecutable"] == "delight", "Incorrect executable"
    assert info["CFBundleShortVersionString"] == expected_version, "Bundle version does not match release tag"
    assert info["NSMicrophoneUsageDescription"], "Microphone permission description missing"
    assert info["LSMinimumSystemVersion"] == "12.0", "Unexpected deployment target"
    run("/usr/bin/lipo", app / "Contents/MacOS/delight", "-verify_arch", architecture)
    run("/usr/bin/codesign", "--verify", "--deep", "--strict", app)
    assert run(app / "Contents/MacOS/delight", "--version") == f"delight {expected_version}", "Executable version does not match bundle"
    for item in app.rglob("*"):
        if item.is_symlink():
            raise ValueError(f"Unexpected bundle link: {item}")
    libraries = run("/usr/bin/otool", "-L", app / "Contents/MacOS/delight").splitlines()[1:]
    for line in libraries:
        library = line.strip().split(" (", 1)[0]
        if not library.startswith(("/System/Library/", "/usr/lib/")):
            raise ValueError(f"Non-system runtime dependency must be bundled: {library}")


def mac_package(args):
    tag = f"v{version()}"
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    architecture = {"arm64": "arm64", "x64": "x86_64"}[args.arch]
    target = {"arm64": "aarch64-apple-darwin", "x64": "x86_64-apple-darwin"}[args.arch]
    binary = ROOT / "target" / target / "release/delight"
    with tempfile.TemporaryDirectory(prefix="delight-package-") as temporary:
        base = Path(temporary)
        stage = base / "image"
        app = stage / "Delight.app"
        contents = app / "Contents"
        (contents / "MacOS").mkdir(parents=True)
        resources = contents / "Resources"
        resources.mkdir()
        shutil.copy2(binary, contents / "MacOS/delight")
        (contents / "MacOS/delight").chmod(0o755)
        iconset = base / "Delight.iconset"
        iconset.mkdir()
        for size in [16, 32, 128, 256, 512]:
            for scale in [1, 2]:
                name = f"icon_{size}x{size}{'@2x' if scale == 2 else ''}.png"
                run("/usr/bin/sips", "-z", size * scale, size * scale, ROOT / "assets/branding/delight-logo.png", "--out", iconset / name)
        run("/usr/bin/iconutil", "-c", "icns", iconset, "-o", resources / "Delight.icns")
        shutil.copy2(ROOT / "packaging/Delight.icns.attribution", resources / "Delight.icns.attribution")
        info = {
            "CFBundleName": "Delight", "CFBundleDisplayName": "Delight", "CFBundleIdentifier": BUNDLE_ID,
            "CFBundleExecutable": "delight", "CFBundlePackageType": "APPL", "CFBundleIconFile": "Delight.icns",
            "CFBundleShortVersionString": version(), "CFBundleVersion": version(), "LSMinimumSystemVersion": "12.0",
            "LSApplicationCategoryType": "public.app-category.video", "NSHighResolutionCapable": True,
            "NSMicrophoneUsageDescription": "Delight uses your microphone when you record audio for a composition.",
            "CFBundleDocumentTypes": [{"CFBundleTypeName": "Delight Project", "CFBundleTypeRole": "Editor", "LSHandlerRank": "Owner", "CFBundleTypeExtensions": ["ecproj", "ecprojx"]}],
            "NSHumanReadableCopyright": "Delight contributors. Includes MIT/Apache-2.0 components; see included notices.",
        }
        (contents / "Info.plist").write_bytes(plistlib.dumps(info))
        for notice in NOTICES:
            shutil.copy2(ROOT / notice, resources / notice)
        # Ad-hoc signing is required on Apple Silicon. This is not Developer ID notarization.
        identity = os.environ.get("MACOS_SIGNING_IDENTITY", "-")
        entitlements = base / "entitlements.plist"
        entitlements.write_bytes(plistlib.dumps({"com.apple.security.device.audio-input": True}))
        options = ["--options", "runtime", "--timestamp", "--entitlements", entitlements] if identity != "-" else []
        run("/usr/bin/codesign", "--force", "--sign", identity, *options, app)
        verify_mac(app, version(), architecture)
        (stage / "Applications").symlink_to("/Applications")
        (stage / "Install.txt").write_text("Drag Delight.app to Applications, then open the installed application.\nThis build is not notarized by Apple unless marked as notarized in its release notes.\n")
        dmg = output / f"Delight-macos-{args.arch}.dmg"
        if dmg.exists():
            raise ValueError("Refusing to replace an existing package")
        # hdiutil's automatic sizing can under-allocate the image filesystem after signing.
        # Give HFS+ explicit metadata/headroom instead of relying on the host's default format.
        payload = sum(item.stat().st_size for item in stage.rglob("*") if item.is_file() and not item.is_symlink())
        image_mib = (payload + 1024**2 - 1) // 1024**2 + 64
        free = shutil.disk_usage(output).free
        if free < (image_mib * 2 + 64) * 1024**2:
            raise RuntimeError(f"Not enough runner disk space for DMG staging: {free} bytes free")
        print(f"DMG payload {payload} bytes; image capacity {image_mib} MiB; runner free {free} bytes", flush=True)
        run("/usr/bin/hdiutil", "create", "-volname", "Delight", "-fs", "HFS+", "-size", f"{image_mib}m", "-srcfolder", stage, "-format", "UDZO", dmg)
        if os.environ.get("MACOS_NOTARY_PROFILE"):
            run("xcrun", "notarytool", "submit", dmg, "--keychain-profile", os.environ["MACOS_NOTARY_PROFILE"], "--wait")
            run("xcrun", "stapler", "staple", dmg)
        run("/usr/bin/hdiutil", "verify", dmg)
        write_manifest(output / f"macos-{args.arch}.manifest.json", tag, {f"macos-{args.arch}": asset(dmg, tag)})


def verify_images(args):
    platforms = {}
    for arch, architecture in [("arm64", "arm64"), ("x64", "x86_64")]:
        dmg = args.assets.resolve() / f"Delight-macos-{arch}.dmg"
        run("/usr/bin/hdiutil", "verify", dmg)
        with tempfile.TemporaryDirectory(prefix="delight-verify-") as temporary:
            mount = Path(temporary) / "mount"
            mount.mkdir()
            run("/usr/bin/hdiutil", "attach", "-readonly", "-nobrowse", "-noautoopen", "-mountpoint", mount, dmg)
            try:
                # Inspect foreign architecture without executing it; each build runner executes its own package.
                app = mount / "Delight.app"
                info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
                assert info["CFBundleIdentifier"] == BUNDLE_ID and info["CFBundleShortVersionString"] == stable(args.tag)
                assert info["CFBundleExecutable"] == "delight"
                run("/usr/bin/lipo", app / "Contents/MacOS/delight", "-verify_arch", architecture)
                run("/usr/bin/codesign", "--verify", "--deep", "--strict", app)
            finally:
                run("/usr/bin/hdiutil", "detach", mount)
        platforms[f"macos-{arch}"] = asset(dmg, args.tag)
    write_manifest(args.output, args.tag, platforms)


def manifest(args):
    platforms = {}
    for source in args.assets.glob("*.manifest.json"):
        data = json.loads(source.read_text(encoding="utf-8-sig"))
        assert data["tag"] == args.tag and data["version"] == stable(args.tag) and data["schema"] == 1
        for platform, entry in data["platforms"].items():
            if platform in platforms:
                raise ValueError(f"Duplicate platform {platform}")
            filename = entry["url"].rsplit("/", 1)[-1]
            assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", filename)
            expected = ".dmg" if platform.startswith("macos-") else ".exe"
            assert filename.endswith(expected)
            assert entry == asset(args.assets / filename, args.tag), "Package changed after platform verification"
            platforms[platform] = entry
    assert set(platforms) == {"windows-x64", "macos-arm64", "macos-x64"}, "Every release requires Windows and both Mac architectures"
    write_manifest(args.output, args.tag, platforms)
    if args.notes:
        data = json.loads(args.output.read_text())
        data["notes"] = args.notes.read_text()[:4000]
        args.output.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    mac = sub.add_parser("mac")
    mac.add_argument("--arch", choices=["arm64", "x64"], required=True)
    mac.add_argument("--output", type=Path, default=ROOT / "dist")
    mac.set_defaults(func=mac_package)
    verify = sub.add_parser("verify-images")
    verify.add_argument("--tag", required=True)
    verify.add_argument("--assets", type=Path, required=True)
    verify.add_argument("--output", type=Path, required=True)
    verify.set_defaults(func=verify_images)
    combine = sub.add_parser("manifest")
    combine.add_argument("--tag", required=True)
    combine.add_argument("--assets", type=Path, required=True)
    combine.add_argument("--output", type=Path, required=True)
    combine.add_argument("--notes", type=Path)
    combine.set_defaults(func=manifest)
    args = parser.parse_args()
    args.func(args)
