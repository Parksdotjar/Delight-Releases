# Delight releases

Official downloads and update feed for Delight, a visual effects desktop application.

| Platform | Download |
| --- | --- |
| Windows x64 | [Windows ZIP](https://github.com/Parksdotjar/Delight-Releases/releases/latest/download/Delight-windows-x64.zip) |
| macOS, Apple Silicon | [Apple Silicon DMG](https://github.com/Parksdotjar/Delight-Releases/releases/latest/download/Delight-macos-arm64.dmg) |
| macOS, Intel | [Intel DMG](https://github.com/Parksdotjar/Delight-Releases/releases/latest/download/Delight-macos-x64.dmg) |

Extract the Windows ZIP into a writable folder and run Delight.exe. On macOS, open the matching DMG and drag Delight.app into Applications before launching or updating it. Mac packages are available starting with 0.0.3.

Mac builds are ad-hoc signed and are not notarized by Apple. First launch may require explicit approval in System Settings > Privacy & Security; managed Macs may prohibit unnotarized apps. No script changes Gatekeeper settings or removes quarantine. See the release notes for tested systems and remaining limitations.

## Updates

Both platforms check the same [latest.json feed](https://github.com/Parksdotjar/Delight-Releases/releases/latest/download/latest.json). The sidebar update indicator downloads the Windows EXE or the Mac DMG for the running architecture. The application verifies size/checksum and package identity, prompts to save, installs after normal shutdown, and retains the previous executable or app bundle for rollback.

Projects and settings are stored separately. A writable installation folder is required; updating from a mounted DMG is not supported. File hashes verify download integrity against the HTTPS feed and are not publisher signatures.

## Publishing

The private Delight-Studio Desktop builds workflow builds and tests Windows x64, macOS arm64 and macOS x64 for every stable tag. Publication is gated on all three builds and native smoke checks. It uploads complete assets and latest.json to a draft release before marking it published/latest. Never replace an announced binary in place; increment the version.

For a manual release, attach Delight.exe, Delight-macos-arm64.dmg and Delight-macos-x64.dmg plus the Windows installation ZIP and required notices before publishing. Generate update feed verifies EXE product/version/processor on Windows and mounts/verifies both DMGs on macOS. It publishes a combined schema-1 manifest only when all platforms match the stable tag. Use workflow_dispatch with the tag if assets were attached after publication.

The existing Windows-only 0.0.2 release remains available. New versions require all three platforms. The editor source stays private; this repository contains distribution files and release automation only.
