# Delight releases

Official Windows releases and update feed for Delight Studio. This repository hosts release files and feed automation; the editor source is maintained separately.

## Publishing an update

1. Set the app workspace version in `Cargo.toml` to the new version, for example `0.0.2`, and update the lockfile. Build and test that version. On Windows, set `DELIGHT_REQUIRE_WINRES=1` and build with `cargo build -p delight --release --locked` so the EXE has required version metadata.
2. Create a **draft release** here with a stable tag such as `v0.0.2`. Attach the standalone application EXE (for example `Delight.exe` or `Delight-windows-x64.exe`) and release notes. Include the license/attribution files required for distribution. Do not upload an installer as the app EXE.
3. Publish the release and mark it as the latest release. The **Generate update feed** workflow validates the EXE's product, version and processor, calculates its size and SHA-256, and attaches `latest.json` automatically. Wait for its green check before announcing the update.
4. Installed updater-enabled apps check at launch and every six hours. A blue circle with an upward arrow appears at the bottom of the left sidebar when a newer compatible version exists. Users can also run **Check for Delight Updates** from the command palette. Clicking the indicator opens the update window; **Update and restart** downloads, verifies, prompts to save if necessary, and relaunches the saved project.

Upload the EXE **before** publishing. If you attach it later, use **Actions → Generate update feed → Run workflow** with the published tag, or edit/save the published release to regenerate its manifest. Tags alone do not update the feed. Drafts and prereleases are excluded.

The first public release is `0.0.2` and includes the updater. Download and extract its Windows ZIP once to install. Existing updater-enabled `0.0.1` development builds can update directly; earlier EXEs without the updater need a manual download. Every release tag must match the version actually embedded in its EXE.

## Feed and recovery

Feed: https://github.com/Parksdotjar/Delight-Releases/releases/latest/download/latest.json

The app accepts only this repository's stable release asset URLs, never downgrades, verifies file length/SHA-256 and Windows processor before installation, and keeps the previous EXE beside the app as `.delight-update-….previous.exe`. If replacement or process launch fails, it restores the old executable where possible and records an error under the user's Delight settings `Updates` folder. A successful process launch is not a guarantee that the new version is bug-free: retain the previous EXE for manual rollback.

Use a writable folder for the portable app. Program Files or another protected folder may require a manual update. No admin elevation or GitHub login is requested from users. Projects and preferences are kept separately from the executable. New dependencies and companion assets must remain compatible with the portable distribution; this updater replaces the EXE only. SHA-256 checks downloaded bytes against the HTTPS feed; it is not an Authenticode signature.

Do not delete old releases while they are downloading, or replace an announced EXE in place. Publish a new version instead. Release binaries are published only by an explicitly authorized release action.

## Manual manifest generation

```powershell
./New-UpdateManifest.ps1 -Tag v0.0.2 -AssetDirectory ./release-assets -OutputPath ./latest.json -Notes 'Release notes'
```

Attach the generated `latest.json` to the same release. Each platform entry contains `url`, `sha256` and byte `size`; the root contains `schema: 1`, `version`, `tag`, `notes`, and `platforms`. Supported platform keys are `windows-x64`, `windows-arm64` and `windows-x86`.
