# Cold Mac

A minimal, dependency-free MAC address changer for Windows 11.

## What it does

- Lists every physical network adapter Windows knows about, with the MAC
  the system currently reports and any custom value already set.
- Assigns a MAC built from a real vendor OUI plus 3 random bytes, so it
  looks like ordinary hardware to routers, DHCP servers, and OUI lookups.
- Remembers the choice per adapter (keyed by GUID, so renaming the
  adapter does not orphan the setting).
- Optionally re-applies saved MACs at every sign-in via a scheduled task.
- Reverts by deleting the `NetworkAddress` registry value and bouncing the
  adapter; the driver restores the hardware MAC.

## What it does NOT do

- It does not hide you from your ISP. Your ISP identifies your connection
  by the public IP on your router's WAN interface, not your adapter's MAC.
  Use a VPN or Tor for ISP-level anonymity.
- It does not change the router's WAN MAC.
- It does not bypass 802.1X, captive portals, or enterprise NAC.
- It does not read, store, or transmit your hardware MAC. There is no
  backup file, no log, no telemetry, no outbound network call. To revert,
  it simply deletes the value it wrote; the driver falls back to the
  burned-in address from the NIC itself.

## Scope

- Windows 11 x64 or ARM64.
- Python 3.8 or newer.
- Administrator privileges at runtime.
- Wi-Fi, Ethernet, and USB network adapters, subject to the driver
  honouring `NetworkAddress`. The script reports when it does not.

## Install

    install.bat

Copies the script to `%LOCALAPPDATA%\ColdMac`, drops a launcher next to
it, appends that folder to your user `PATH`, and — if run as
administrator — offers to register a logon task that re-applies saved
MACs. Open a new terminal afterwards.

## Usage

    cold-mac --list
    cold-mac --list --all
    cold-mac --interface "Wi-Fi" --random
    cold-mac --interface "Wi-Fi" --random --vendor Intel
    cold-mac --interface "Wi-Fi" --mac 3C970E1A2B3C
    cold-mac --interface "Wi-Fi" --revert
    cold-mac --restore-all
    cold-mac --boot
    cold-mac --no-boot

- `--list` shows physical adapters, the MAC Windows currently reports, the
  custom MAC if one is set, and the vendor name recorded in the config.
- `--list --all` also shows virtual adapters (WAN Miniport, Hyper-V, TAP,
  VPN, Wi-Fi Direct, Bluetooth PAN, NPcap).
- `--random` picks a real vendor OUI from the built-in list and appends 3
  random bytes. `--vendor` pins the vendor.
- `--mac` sets a specific address. First byte must be even (unicast).
- `--revert` clears one adapter and restores the hardware MAC.
- `--restore-all` reverts every adapter in the saved config.
- `--boot` / `--no-boot` register or remove the logon task.

## Locally administered vs vendor MAC

Cold Mac 1.1.0 deliberately does **not** generate `02`-prefixed locally
administered MACs by default, because some routers and NAC systems flag
them. It uses real vendor OUIs instead, which is what actual hardware
presents. If you need a locally administered MAC for a specific test,
pass it via `--mac`.

Note that impersonating a specific vendor's OUI is a different act from
setting a generic local address — in some jurisdictions and network
policies that difference matters. You are responsible for the choice.

## Verifying a spoof

On some Windows drivers, `getmac` and `ipconfig /all` continue to report
the hardware MAC even after a successful registry change; the change is
visible on the wire, just not to local tools. Cold Mac prints a note when
this happens. To confirm the driver accepted the value, open
**Device Manager → Network adapters → your adapter → Properties →
Advanced → Network Address**. If your MAC is there, the driver has it.

The most reliable external check is on another device on the same LAN:

    arp -a

...and look for the IP your machine was assigned. The MAC shown there is
what the network sees.

## Troubleshooting

- **"administrator privileges required"** — right-click Terminal and
  *Run as administrator*. `--list` works without admin.
- **"getmac reports ..." note after applying** — expected on some
  drivers; see the verification section.
- **Adapter disappears after bounce** — some USB Wi-Fi adapters take
  10-20 seconds to re-enumerate. Wait, or replug.
- **Driver ignores the value entirely** — a few Intel Wi-Fi models need
  `PnPCapabilities = 24` under the adapter's class key before they will
  honour `NetworkAddress`. See GUIDE.md.
- **`cold-mac` not recognised** — the new `PATH` only applies to
  terminals opened after `install.bat` ran.

## Legal

MAC address changing is legal in most jurisdictions and is a built-in
Windows 11 privacy feature. It is illegal to use it to evade a lawful
access-control decision (a ban you were given, fraud, unauthorized
access). You are responsible for how you use it.

## License

MIT.