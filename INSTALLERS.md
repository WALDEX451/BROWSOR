# BROWSOR 1.0 beta 1 installers

All installation formats are attached to the same [1.0 beta 1 prerelease](https://github.com/WALDEX451/BROWSOR/releases/tag/v1.0.0-beta.1).

| Package | Platform | Installation |
| --- | --- | --- |
| `BROWSOR-1.0.0-beta.1-windows-x64-setup.exe` | Windows 10/11 x64 | Run the per-user installer; no administrator access required |
| `BROWSOR-1.0.0-beta.1-macos-arm64.dmg` | macOS 13+, Apple Silicon | Drag BROWSOR.app to Applications |
| `BROWSOR-1.0.0-beta.1-macos-x86_64.dmg` | macOS 13+, Intel | Drag BROWSOR.app to Applications |
| `BROWSOR-1.0.0-beta.1-windows-x64.zip` | Windows x64, portable | Extract the complete folder and open BROWSOR.exe |

## Source and packaging

Application source remains commit `d920d45bb88949720c99e89bb292d63f07939a7b`, the existing `v1.0.0-beta.1` tag. Adding installers does not move that tag or change the released application code. The additional packaging recipes and workflows live on `main`.

The build workflow checks out that exact application commit separately from the packaging recipes. macOS `BUILD-INFO.json` records both revisions. The same Python 3.12.10, PySide6 6.11.1 and PyInstaller 6.22.3 are used for all installer targets.

## What the checks establish

Before upload, each installer is opened on a fresh runner for its platform. Windows is installed into a temporary directory; macOS mounts the read-only disk image. The actual packaged executable is launched with a loopback-only debugging port and an offscreen display. The check waits until Chromium reports the local `browsor://home/` page with its expected title. The app and debugging endpoint are then stopped.

This establishes that installation/mounting, bundled libraries, startup and the local start-page resource work in those runner environments. It does not establish compatibility with every computer, GPU, website or authentication provider. Gatekeeper and Windows reputation checks are separate from this startup check.

The workflow records installer SHA-256 hashes with its results. Downloads have an accompanying `INSTALLERS-SHA256SUMS.txt`; the portable ZIP retains its original `SHA256SUMS.txt`.

## Signing

Windows installers and executables are unsigned. macOS bundles have the ad-hoc signatures needed by the runtime, but no Apple Developer ID signature or notarization. No commercial signing credentials have been configured. Follow normal operating-system approval prompts for a copy you trust; system protections should remain enabled.
