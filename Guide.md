# Cold Mac — Technical Guide

## How the change works

Windows drivers for NDIS miniport adapters read an optional registry
value called `NetworkAddress` when the adapter is initialised. If it
is present and parses as 12 hex digits, the driver presents that value
up the stack as the adapter's MAC instead of the burned-in address.

The key lives at:

    HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}\<NNNN>

where `<NNNN>` is a four-digit subkey (0000, 0001, ...). Each subkey
carries `DriverDesc` (the driver's description), `NetCfgInstanceId`
(the adapter GUID), and optionally `NetworkAddress`.

The friendly name ("Wi-Fi") is not in that key. It lives in:

    HKLM\SYSTEM\CurrentControlSet\Control\Network\{4d36e972-e325-11ce-bfc1-08002be10318}\<GUID>\Connection\Name

Cold Mac joins the two: it walks the class key, reads each subkey's
`NetCfgInstanceId`, then resolves the friendly name from the
connection key.

## Why bounce the adapter

`NetworkAddress` is read at miniport initialisation. Writing the value
while the adapter is up does nothing until the next init. `netsh
interface set interface <name> admin=disable` followed by `enable`
forces a tear-down and re-init, which is the cheapest way to make the
new value take effect without a reboot.

## Why the verification step

A minority of drivers accept the registry write but ignore the value,
or normalise it (for example, forcing the local bit). Cold Mac reads
the adapter's reported MAC after the bounce and compares. On mismatch
it returns exit code 2 and tells you, rather than claiming success.

## Why no backup file

The hardware MAC is the backup. Deleting `NetworkAddress` and
bouncing restores it because the driver falls back to the EEPROM /
firmware value. A backup file would be the *only* artifact Cold Mac
could leave behind, and it is unnecessary. This is why the tool can
honestly claim it leaves no trace of the real MAC.

## Why locally administered (`02`)

The IEEE defines bit 0 of the first octet as the I/G bit (0 =
unicast) and bit 1 as the U/L bit (1 = locally administered). A MAC
starting with `02` is therefore unicast and explicitly marked as
software-assigned. Networks that log MACs will see that the address
was set by software, which is the honest signal. If you need to blend
in with real hardware, supply a vendor OUI with `--mac`; understand
that doing so is impersonation and carries different legal weight.

## What this does not solve

MAC is layer 2. It is visible to the AP, to switches, and to anything
on the same broadcast domain. It is not visible to your ISP, which
operates at layer 3 and identifies you by the public IP on the WAN
side of your router. If your threat model is "my ISP should not know
who I am," MAC randomisation is irrelevant to it; VPN or Tor is the
relevant tool. If your threat model is "the café Wi-Fi should not
track my laptop across visits, and the router should not see my real
hardware address," Cold Mac is the right tool.