# Desktop releases

Delight source and build automation live in the private `Parksdotjar/Delight-Studio` repository. Public packages and `latest.json` live in `Parksdotjar/Delight-Releases`.

Every stable update must contain all three packages from the same version/source revision:

- `Delight.exe` for Windows x64, plus `Delight-windows-x64.zip` for initial installation and notices.
- `Delight-macos-arm64.dmg` for Apple Silicon.
- `Delight-macos-x64.dmg` for Intel Macs.

## Building

The Desktop builds workflow uses GitHub-hosted Windows, Apple Silicon and Intel macOS machines. It runs updater tests including native subprocess handoff, builds with the committed lockfile, packages each OS, launches the packaged application, creates/saves/reopens a project, applies an effect, exercises playback, and renders frames. Artifacts include packages, logs and UI screenshots. A failed platform prevents the combined release job.

Local macOS prerequisites: Rust 1.99 and Xcode command line tools. Set `MACOSX_DEPLOYMENT_TARGET=12.0`; build `cargo build -p delight --release --locked --target aarch64-apple-darwin` (or `x86_64-apple-darwin`) and run `python3 packaging/release.py mac --arch arm64` (or `x64`). Native checks run on macOS 15; the deployment target alone does not certify older systems.

The bundle contains the real wing icon, document associations, microphone permission description, and required notices. It uses native file dialogs, menus, Command shortcuts, CoreAudio and wgpu's Metal backend. Packaging rejects non-system dynamic libraries unless explicitly bundled in a future change.

## Publishing each update

1. Develop on a feature branch. Bump the workspace version and lockfile, including xtask, and update `packaging/RELEASE_NOTES.md`.
2. Run Desktop builds with publication disabled. Review all three jobs and smoke artifacts.
3. Merge the reviewed source to main. Create/push a matching stable `vX.Y.Z` tag, or explicitly dispatch with `publish: true`. A tag must match the actual workspace version.
4. The workflow rebuilds/tests all packages, creates a complete manifest, uploads a draft release with all assets/notices, and only then marks it published/latest. Existing release versions are never overwritten.
5. Verify the public feed and download links. No release is complete if one platform is missing.

The private build repository needs `DELIGHT_RELEASE_TOKEN`, a token with contents-write access to the public release repository. Never commit it. The public repository also keeps `New-UpdateManifest.ps1`, `release.py` and `.github/workflows/update-feed.yml` as a verified fallback for manual releases. Manual feed regeneration validates EXE metadata on Windows and mounts/validates both DMGs on macOS before combining checksums. Legacy Windows-only 0.0.2 remains downloadable; new releases require all platforms.

## Signing

Current Mac builds are ad-hoc signed for executable integrity and Apple Silicon compatibility. They are not Developer ID signed or Apple notarized. First launch may require explicit approval in macOS Privacy & Security; managed systems may prohibit this. Do not strip quarantine or change Gatekeeper settings in scripts.

To add notarization later, provision a temporary CI keychain with a Developer ID Application certificate, set `MACOS_SIGNING_IDENTITY`, and provide a `MACOS_NOTARY_PROFILE` for `notarytool`. The packager signs with hardened runtime when an identity is supplied, submits the DMG, and staples the notarization ticket. Signing credentials belong only in protected CI secrets/keychains.

## Updates and rollback

Both OSes use the same stable feed and sidebar update controls. Windows selects the EXE; macOS selects its processor's DMG. Each checks SHA-256, size, version and native package identity before installation. The Mac updater mounts read-only, stages a complete verified bundle beside the installed app, waits for normal guarded shutdown, swaps bundles, and reopens the saved project via LaunchServices. A writable installation folder is required. Apps running from a mounted DMG or App Translocation must first be installed into Applications.

Previous EXEs/apps remain beside the installation under a `.delight-update-...previous` name. Replacement or immediate relaunch failures restore the old copy where possible. Successful process launch is not proof of all subsequent application behavior; retained copies allow manual rollback. Projects/preferences are outside the application bundle. Errors are recorded in the user settings Updates folder. The feed is HTTPS/checksum-verified, not an independent release signature.
