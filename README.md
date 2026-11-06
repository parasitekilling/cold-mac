# Cold Mac 1.2.0

A minimal, dependency-free MAC address configuration utility for Windows 11.

Built for security researchers, red teamers, and privacy-conscious users who need a reliable way to test network access controls without risking a broken network connection. 

## The "Honest" Approach to MAC Spoofing

Most Windows MAC changers silently fail. They write a registry key, tell the user "Success!", and walk away. Meanwhile, the network card completely ignores the change.

Cold Mac is different. It uses structured Windows API calls (`Get-NetAdapter`), strict validation, and **automatic rollback**. 

If your network driver refuses the MAC change (which many modern Intel and Realtek cards do), Cold Mac will detect the failure, safely restore your original configuration, and tell you exactly what happened. You will never be left offline.

## Features

- **Interactive Menu & CLI:** Double-click the launcher for a guided experience, or use CLI commands for automation.
- **Automatic Rollback:** If the driver rejects the new MAC, the tool restores the original registry setting and restarts the adapter.
- **Zero Dependencies:** Pure Python 3 standard library. No external packages, no compiled binaries, no kernel drivers.
- **Strict Validation:** Only accepts locally administered, unicast MAC addresses (e.g., `02:11:22:33:44:55`) to prevent network collisions.
- **Safe Operations:** Maps the network adapter GUID to the correct registry key, avoiding the fragile text-parsing used by older tools.
- **No Telemetry:** Your data stays on your machine.

## ⚠️ Known Driver Limitations

Modern Windows drivers often handle MAC addresses at the hardware/firmware level and will ignore software overrides. 
- **Intel Wi-Fi (e.g., AX201):** Officially does not support custom MAC addresses.
- **Realtek USB/Wi-Fi (e.g., 8812AU):** Many modern Realtek drivers ignore the `NetworkAddress` registry key.
- **Ethernet (Realtek/Intel PCIe):** Usually works perfectly.

If your adapter ignores the change, Cold Mac will report `NOT VERIFIED` and automatically roll back to your original MAC.

## Requirements
- Windows 11 (or Windows 10)
- Python 3.10 or newer
- Administrator privileges (for changing MAC addresses)

## Installation

1. Clone this repository or download the source code.
2. Ensure Python is installed and added to your system `PATH`.
3. No `pip install` is required.

## Usage

### 1. Interactive Mode (Recommended)
Double-click `cold-mac.bat` (or run `py -3 cold_mac.py` without arguments) to launch the Coldroom interface.

### 2. Command Line Interface (CLI)
Run these commands from an **Administrator** terminal:

**List available adapters:**
```powershell
py -3 cold_mac.py list
Set a random locally administered MAC:

powershell
py -3 cold_mac.py set "Wi-Fi" --random
Set a specific MAC:

powershell
py -3 cold_mac.py set "Wi-Fi" --mac 02:11:22:33:44:55
Restore the original hardware MAC:

powershell
py -3 cold_mac.py restore "Wi-Fi"
Note: You must use the exact adapter name or GUID shown in the list command.

How it works
You select an adapter.

Cold Mac maps its Interface GUID to the correct Registry Class Key.

It backs up the original NetworkAddress state to %LOCALAPPDATA%\ColdMac.

It writes the new MAC and restarts the adapter.

It reads back the adapter's reported MAC.

If the MAC matches -> MATCH. If it fails -> NOT VERIFIED (and it rolls back).

License
MIT License. See LICENSE for details.
Created by parasitekilling.