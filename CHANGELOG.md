# Changelog

## 1.0.0-beta.1

The second design iteration of BROWSOR, published as the first beta of 1.0.

### New

- A complete Windows x64 portable package, including the start page and icons.
- A visible beta badge, About dialog, engine versions and links to release notes and issues.
- **Go anywhere** (`Ctrl+K`): search your open tabs, favorites and browser actions. Enter a new address or search query from the same dialog.
- Import favorites from browser HTML or BROWSOR JSON; export in either format. Invalid addresses and duplicates are skipped, with an import summary.
- Optional restoration of up to 20 tabs on the next launch. Turn it on in preferences; it is off by default.
- Copy a page's title, address and selected text for your AI assistant. Sharing happens when you paste and send it yourself.
- A reload control in the AI panel and clearer cookie-storage language.

### Improved

- More consistent styling, accent-aware setup navigation and keyboard guidance on the start page.
- Address-bar updates after tab reordering.
- Cancelled navigation no longer replaces a page with the network error view.
- Existing English interface and migration of older Dutch settings are retained.
- Release packaging has version metadata, a Windows icon, checksums and dependency notices.

### Beta limitations

- Windows x64 is the packaged target. Other platforms are source-only and have not been validated for this release.
- This build is unsigned and has no automatic updater. Windows may show an unknown-publisher warning.
- Some Google, Apple or AI service sign-in flows reject embedded browsers. BROWSOR does not bypass provider restrictions.
- No BROWSOR cloud account, cross-device synchronization, extension store or password manager.
- The tracker filter uses a small fixed domain list. It does not block all tracking.
- Tab restoration happens after a normal app close, stores URLs locally and restores at most 20 tabs; it is not crash recovery.
- Favorite folders are flattened on import; the limit is 100 favorites. The first five appear on the start page.
- Website sign-in persistence changes after restarting. Disabling it does not erase a previously saved persistent profile.
- Website compatibility, DRM video, passkeys, camera/microphone flows and accessibility have not received a full compatibility audit.
