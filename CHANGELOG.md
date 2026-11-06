# Changelog

## 1.1.0 — 2026-11-06

### Added

- Vendor-prefixed MAC generation. `--random` now builds the address from
  a curated list of real vendor OUIs plus 3 random bytes. `--vendor`
  pins the vendor.
- Persistent per-interface config at `%LOCALAPPDATA%\ColdMac\config.json`,
  keyed by adapter GUID. Stores only the spoofed MAC, never the hardware
  MAC.
- `--apply-saved` to re-apply all stored MACs. Used by the logon task.
- `--boot` / `--no-boot` to register or remove a `schtasks` logon task
  that re-applies saved MACs at every sign-in. `install.bat` prompts for
  this when run as administrator.
- `--restore-all` to revert every adapter in the config at once.
- `--all` to include virtual adapters in `--list`.
- Post-apply verification note explaining when `getmac` masks a
  successful spoof.

### Changed

- Adapter enumeration excludes virtual adapters by default (WAN Miniport,
  Wi-Fi Direct, Hyper-V, TAP, VPN, Bluetooth PAN, NPcap, ISATAP, Teredo,
  loopback).
- Adapter bounce retried twice for USB re-enumeration timing.
- Interface identification for the config uses GUID, so renaming the
  adapter does not orphan the saved MAC.

### Removed

- Fully random `02`-prefixed MAC generation as the default. Use `--mac`
  for a manual override.

## 1.0.0 — 2026-11-06

- Initial release.