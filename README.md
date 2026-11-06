# Cold Mac

A minimal, dependency-free MAC address changer for Windows 11.

## What it does

- Lists every network adapter Windows knows about, with its friendly
  name, driver description, and current MAC.
- Sets a custom MAC address on any adapter by writing the standard
  `NetworkAddress` registry value under the adapter's class key.
- Bounces the adapter (disable / enable) so the driver re-reads the
  value.
- Reverts by deleting `NetworkAddress`; the driver restores the
  hardware MAC automatically.

## What it does NOT do

- It does not hide you from your ISP. Your ISP identifies your
  connection by the public IP on your router's WAN interface, not by
  your adapter's MAC. Use a VPN or Tor for ISP-level anonymity.
- It does not change the router's WAN MAC. If you need that, change it
  in the router's admin panel.
- It does not bypass 802.1X, captive portals, or enterprise NAC. Those
  systems authenticate on more than MAC.
- It does not log, phone home, or store your original MAC anywhere.
  There is no backup file, no telemetry, no network call.

## Scope of the change

- Windows 11, x64 or ARM64.
- Python 3.8 or newer (`py -3` launcher or `python` on PATH).
- Administrator privileges (the adapter class key is HKLM).
- Both Wi-Fi and Ethernet adapters are supported, subject to the
  driver honouring `NetworkAddress`. Most do; a few do not, and the
  tool will say so in its verification step.

## Install

    install.bat

This copies the script to `%LOCALAPPDATA%\ColdMac`, drops a launcher
next to it, and appends that folder to your user `PATH`. Open a new
terminal afterwards.

## Usage

    cold-mac --list
    cold-mac --interface "Wi-Fi" --random
    cold-mac --interface "Wi-Fi" --mac 02AABBCCDDEE
    cold-mac --interface "Wi-Fi" --revert

- `--list` / `-l` shows all adapters, the MAC the system currently
  reports, and the custom value if one is set.
- `--random` / `-r` generates a locally administered unicast MAC
  (first octet `02`) and applies it.
- `--mac` / `-m` applies a specific 12-hex-digit MAC. The multicast
  bit of the first octet must be clear.
- `--revert` deletes the custom value and bounces the adapter.

The interface name is the Windows friendly name ("Wi-Fi", "Ethernet",
"Ethernet 2"). `--list` prints the exact strings to use.

## Locally administered addresses

The random generator always produces a MAC whose first octet is `02`,
the IEEE marker for a *locally administered* address. This is honest:
it announces "this address was set by software, not burned in." Some
networks flag locally administered addresses. If you need to blend in
with a specific vendor OUI, pass it with `--mac`. Cold Mac does not
generate vendor OUIs for you, because impersonating a hardware vendor
is a different act with different legal exposure in some
jurisdictions.

## Reverting cleanly

    cold-mac --interface "Wi-Fi" --revert

This removes `NetworkAddress` from the registry. The driver re-reads
the burned-in address from the NIC. Nothing Cold Mac did survives the
revert, because Cold Mac never stored anything.

## Troubleshooting

- **`error: administrator privileges required`** — right-click
  Terminal / PowerShell and *Run as administrator*.
- **`warning: adapter reports ...`** — the driver ignored the
  registry value. Run `--revert` to remove it, then try another
  adapter or a different first octet.
- **Adapter disappears after bounce** — some USB Wi-Fi adapters take
  10-20 seconds to re-enumerate. Wait, or replug.
- **`cold-mac` not recognised** — the new `PATH` only applies to
  terminals opened after `install.bat` ran. Close and reopen.
- **Wi-Fi drops during the change** — expected; the adapter is
  disabled for a few seconds. Reconnect if Windows does not do so
  automatically.

## Legal

MAC address changing is legal in most jurisdictions and is a
first-class privacy feature of Windows 11 itself. It is illegal to
use it to evade a lawful access-control decision (for example,
bypassing a ban imposed by a network you do not own, or committing
fraud). You are responsible for how you use it.

## License

MIT.