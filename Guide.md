# Cold Mac — Technical Guide

## How the change works

Windows NDIS drivers read an optional registry value called
`NetworkAddress` when the adapter initialises. If present and parseable
as 12 hex digits, the driver presents that value up the stack instead of
the burned-in MAC.

Key location:

    HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}\<NNNN>

Friendly name ("Wi-Fi") lives in:

    HKLM\SYSTEM\CurrentControlSet\Control\Network\{4d36e972-e325-11ce-bfc1-08002be10318}\<GUID>\Connection\Name

Cold Mac walks the class key, reads each subkey's `NetCfgInstanceId`,
resolves the friendly name from the connection key, and stores the saved
MAC in `%LOCALAPPDATA%\ColdMac\config.json` keyed by that GUID.

## Why bounce the adapter

`NetworkAddress` is only read at miniport initialisation. Writing it
while the adapter is up does nothing until the next init. `netsh
interface set interface <name> admin=disable` followed by `enable`
forces tear-down and re-init. Cold Mac retries the bounce twice, because
some USB Wi-Fi adapters need a beat to re-enumerate.

## Why the config is keyed by GUID

Friendly names can be renamed by the user. If the config were keyed by
name, renaming `Wi-Fi` to `HomeWiFi` in Windows would orphan the saved
MAC. GUIDs are stable for the lifetime of the adapter.

## Why no backup of the real MAC

The hardware MAC **is** the backup. Deleting `NetworkAddress` and
bouncing restores the burned-in value, because the driver falls back to
the NIC's firmware. Storing the real MAC somewhere would be the only
artifact Cold Mac could possibly leak, and it is unnecessary. This is
why the tool can honestly claim it leaves no trace.

## Why real vendor OUIs by default

A MAC starting with `02` is locally administered — the I/G bit is 0
(unicast) and the U/L bit is 1 (software-assigned). Networks that log
MACs can see this and may treat it as suspicious. A MAC with a real
vendor OUI is indistinguishable from genuine hardware at layer 2.

Cold Mac 1.1.0 uses a curated list of ~28 real vendor OUIs covering
Intel, Realtek, Broadcom, Apple, Dell, HP, Lenovo, ASUS, TP-Link,
Netgear, Samsung, Microsoft, and Qualcomm. Extend `VENDOR_OUI` in
`cold_mac.py` with more if needed. Every entry is at most 6 hex digits;
a 3-byte entry leaves the last 3 bytes random, which is what real NICs
do.

## Why some drivers ignore the value

A minority of NDIS miniport drivers ignore `NetworkAddress` unless a
second value, `PnPCapabilities`, is set to `24` in the same class key.
This is a known quirk of certain Intel Wi-Fi adapters. Cold Mac does
not set `PnPCapabilities` automatically because it changes driver
behaviour more invasively than a MAC override.

If your adapter ignores the value:

1. Open `regedit` as administrator.
2. Navigate to `HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}\<subkey>` for your adapter. Identify it by `DriverDesc`.
3. Create a `DWORD` value named `PnPCapabilities`, set to `24`.
4. Bounce the adapter. Try the Cold Mac command again.

To undo, delete `PnPCapabilities`.

## What this does not solve

MAC is layer 2. It is visible to the access point, switches, and any
host on the same broadcast domain. It is not visible to your ISP, which
operates at layer 3 and identifies your connection by the public IP on
the WAN side of your router. If your threat model is "my ISP should not
know who I am," MAC randomisation is irrelevant; VPN or Tor is the
relevant tool. If your threat model is "the café Wi-Fi should not track
my laptop across visits, and the router should not see my real hardware
address," Cold Mac is the right tool.