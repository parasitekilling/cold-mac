#!/usr/bin/env python3
"""
Cold Mac 1.2.0 — by parasitekilling

Windows-only, standard-library MAC configuration utility.
No kernel driver. No downloads. No telemetry.

A MATCH means Windows reports the requested address.
It does not establish what an external access point observes.

Run locally: restarting an adapter interrupts its connection.
"""

import argparse
import base64
import ctypes
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import uuid

VERSION = "1.2.0"
CLASS_KEY = (
    r"SYSTEM\CurrentControlSet\Control\Class"
    r"\{4d36e972-e325-11ce-bfc1-08002be10318}"
)

BANNER = r"""
 ██████╗ ██████╗ ██╗     ██████╗     ███╗   ███╗ █████╗  ██████╗
██╔════╝██╔═══██╗██║     ██╔══██╗    ████╗ ████║██╔══██╗██╔════╝
██║     ██║   ██║██║     ██║  ██║    ██╔████╔██║███████║██║
██║     ██║   ██║██║     ██║  ██║    ██║╚██╔╝██║██╔══██║██║
╚██████╗╚██████╔╝███████╗██████╔╝    ██║ ╚═╝ ██║██║  ██║╚██████╗
 ╚═════╝ ╚═════╝ ╚═════╝ ╚═════╝     ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝
             C O L D   M A C  //  by parasitekilling
"""


def is_admin():
    return bool(ctypes.windll.shell32.IsUserAnAdmin())


def canonical_guid(value):
    return str(uuid.UUID(str(value).strip("{}")))


def compact_mac(value):
    return re.sub(r"[^0-9A-Fa-f]", "", value or "").upper()


def validate_mac(value):
    value = value.strip()

    valid = (
        re.fullmatch(r"[0-9A-Fa-f]{12}", value)
        or re.fullmatch(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", value)
        or re.fullmatch(r"(?:[0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}", value)
    )

    if not valid:
        raise ValueError(
            "Use 12 hex digits or six colon/hyphen-separated octets."
        )

    value = compact_mac(value)

    if (int(value[:2], 16) & 3) != 2:
        raise ValueError(
            "Use a locally administered unicast address, "
            "for example 02:11:22:33:44:55."
        )

    return value


def random_mac():
    value = bytearray(secrets.token_bytes(6))
    value[0] = (value[0] & 0xFC) | 0x02
    return value.hex().upper()


def pretty_mac(value):
    value = compact_mac(value)
    if len(value) != 12:
        return value or "unavailable"
    return ":".join(value[i:i + 2] for i in range(0, 12, 2))


def powershell(script):
    executable = (
        Path(os.environ["SystemRoot"])
        / "System32"
        / "WindowsPowerShell"
        / "v1.0"
        / "powershell.exe"
    )

    prefix = (
        "$ErrorActionPreference='Stop';"
        "[Console]::OutputEncoding=[Text.UTF8Encoding]::new();"
    )

    encoded = base64.b64encode(
        (prefix + script).encode("utf-16-le")
    ).decode("ascii")

    result = subprocess.run(
        [
            str(executable),
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
            encoded,
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
        shell=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "PowerShell operation failed."
        )

    return result.stdout.strip().lstrip("\ufeff")


def get_adapters():
    text = powershell(
        "@(Get-NetAdapter -Physical | "
        "Select-Object Name,InterfaceDescription,InterfaceGuid,"
        "MacAddress,Status,DriverVersion,DriverInformation) | "
        "ConvertTo-Json -Depth 3 -Compress"
    )

    if not text:
        return []

    result = json.loads(text)
    return result if isinstance(result, list) else [result]


def find_adapter(target):
    matches = [
        adapter
        for adapter in get_adapters()
        if adapter["Name"].casefold() == target.casefold()
        or str(adapter["InterfaceGuid"]).strip("{}").casefold()
        == target.strip("{}").casefold()
    ]

    if len(matches) != 1:
        raise ValueError(
            "Specify one exact adapter name or GUID from the list."
        )

    return matches[0]


def registry_key_for(target_guid):
    import winreg

    matches = []

    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE, CLASS_KEY
    ) as root:
        index = 0

        while True:
            try:
                subkey = winreg.EnumKey(root, index)
            except OSError:
                break

            index += 1

            if not subkey.isdigit():
                continue

            try:
                with winreg.OpenKey(root, subkey) as key:
                    value = winreg.QueryValueEx(
                        key, "NetCfgInstanceId"
                    )[0]

                if canonical_guid(value) == target_guid:
                    matches.append(CLASS_KEY + "\\" + subkey)

            except (OSError, ValueError):
                continue

    if len(matches) != 1:
        raise RuntimeError(
            "Could not uniquely match the adapter to its registry key."
        )

    return matches[0]


def read_setting(path):
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE, path
    ) as key:
        try:
            value, kind = winreg.QueryValueEx(
                key, "NetworkAddress"
            )
        except FileNotFoundError:
            return {"exists": False, "value": None}

    if kind != winreg.REG_SZ:
        raise RuntimeError(
            "Existing NetworkAddress is not REG_SZ; refusing to modify."
        )

    return {"exists": True, "value": value}


def write_setting(path, setting):
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE,
        path,
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        if setting["exists"]:
            winreg.SetValueEx(
                key,
                "NetworkAddress",
                0,
                winreg.REG_SZ,
                setting["value"],
            )
        else:
            try:
                winreg.DeleteValue(key, "NetworkAddress")
            except FileNotFoundError:
                pass


def restart_adapter(target_guid):
    target_guid = canonical_guid(target_guid)

    powershell(
        "$a=@(Get-NetAdapter -Physical | Where-Object {"
        "([string]$_.InterfaceGuid).Trim('{}') -eq '"
        + target_guid
        + "'});"
        "if($a.Count -ne 1){throw 'Adapter unavailable'};"
        "$a[0] | Restart-NetAdapter -Confirm:$false"
    )


def current_mac(target_guid):
    for adapter in get_adapters():
        if canonical_guid(adapter["InterfaceGuid"]) == target_guid:
            return compact_mac(adapter.get("MacAddress"))
    return ""


def backup_path(target_guid):
    return (
        Path(os.environ["LOCALAPPDATA"])
        / "ColdMac"
        / (canonical_guid(target_guid) + ".json")
    )


def load_backup(path, target_guid):
    data = json.loads(path.read_text(encoding="utf-8"))

    if data.get("schema") != 1 or data.get("guid") != target_guid:
        raise RuntimeError("Invalid backup identity or schema.")

    setting = data.get("original")

    if not isinstance(setting, dict):
        raise RuntimeError("Invalid backup configuration.")

    if type(setting.get("exists")) is not bool:
        raise RuntimeError("Invalid backup existence flag.")

    if setting["exists"] and not isinstance(setting.get("value"), str):
        raise RuntimeError("Invalid original registry value.")

    return data


def create_backup(path, adapter, target_guid, original):
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "schema": 1,
        "guid": target_guid,
        "name": adapter["Name"],
        "original": original,
    }

    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        load_backup(path, target_guid)


def require_admin():
    if not is_admin():
        raise PermissionError(
            "Open a local terminal as Administrator to change settings."
        )


def confirm_change(adapter, assume_yes=False):
    if adapter.get("Status") == "Disabled":
        raise RuntimeError(
            "Enable this adapter yourself before modifying it."
        )

    print("\nAdapter:", adapter["Name"])
    print("Device: ", adapter["InterfaceDescription"])
    print("WARNING: The selected adapter will restart and disconnect.")
    print("Do not use through a remote session.")
    print("Only modify equipment and networks you are authorized to use.")

    if not assume_yes:
        if input("Type APPLY to continue: ").strip() != "APPLY":
            print("Cancelled. No changes made.")
            return False

    return True


def apply_mac(target, value, assume_yes=False):
    require_admin()

    requested = validate_mac(value)
    adapter = find_adapter(target)
    target_guid = canonical_guid(adapter["InterfaceGuid"])

    if compact_mac(adapter.get("MacAddress")) == requested:
        print("Already reported by Windows. No change made.")
        return 0

    for other in get_adapters():
        if (
            canonical_guid(other["InterfaceGuid"]) != target_guid
            and compact_mac(other.get("MacAddress")) == requested
        ):
            raise ValueError(
                "Another local adapter already reports this address."
            )

    key = registry_key_for(target_guid)
    previous = read_setting(key)
    path = backup_path(target_guid)

    if path.exists():
        load_backup(path, target_guid)

    print("Requested:", pretty_mac(requested))

    if not confirm_change(adapter, assume_yes):
        return 1

    create_backup(path, adapter, target_guid, previous)

    try:
        write_setting(key, {"exists": True, "value": requested})
        restart_adapter(target_guid)

        observed = ""

        for _ in range(8):
            time.sleep(2)
            observed = current_mac(target_guid)

            if observed == requested:
                print("\nMATCH:", pretty_mac(observed))
                print("Windows reports the requested address.")
                print("External verification has NOT been performed.")
                print("Original-setting backup:", path)
                return 0

        raise RuntimeError(
            "Requested address not observed. Windows reports: "
            + pretty_mac(observed)
        )

    except (Exception, KeyboardInterrupt) as error:
        print("\nNOT VERIFIED:", error or "Interrupted.")

        try:
            write_setting(key, previous)
            restart_adapter(target_guid)

            if read_setting(key) != previous:
                raise RuntimeError(
                    "Restored registry value did not match the snapshot."
                )

            print("Pre-attempt registry configuration restored.")
            print("Adapter restart command completed.")
            print("Network connectivity has not been independently verified.")

        except (Exception, KeyboardInterrupt) as recovery:
            print("RECOVERY FAILED:", recovery or "Interrupted.")
            print("Backup retained:", path)
            print("Use restore locally after resolving the failure.")

        return 2


def restore_mac(target, assume_yes=False):
    require_admin()

    adapter = find_adapter(target)
    target_guid = canonical_guid(adapter["InterfaceGuid"])
    path = backup_path(target_guid)

    if not path.exists():
        raise RuntimeError("No saved original configuration for this adapter.")

    data = load_backup(path, target_guid)
    key = registry_key_for(target_guid)

    if not confirm_change(adapter, assume_yes):
        return 1

    write_setting(key, data["original"])

    try:
        restart_adapter(target_guid)
    except (Exception, KeyboardInterrupt):
        print("Original registry setting was written.")
        print("Adapter restart did not complete; manual recovery may be needed.")
        print("Backup retained:", path)
        raise

    if read_setting(key) != data["original"]:
        raise RuntimeError("Original registry configuration was not restored.")

    print("\nOriginal registry configuration restored.")
    print("Windows reports:", pretty_mac(current_mac(target_guid)))
    print("Backup retained:", path)
    print("Connectivity and external address have not been verified.")
    return 0


def display_adapters():
    adapters = get_adapters()

    if not adapters:
        print("No physical adapters found.")
        return []

    for index, adapter in enumerate(adapters, 1):
        print(f"\n[{index}] {adapter['Name']}")
        print("    Device: ", adapter["InterfaceDescription"])
        print("    MAC:    ", pretty_mac(adapter.get("MacAddress")))
        print("    Status: ", adapter.get("Status", "unknown"))
        print("    GUID:   ", adapter["InterfaceGuid"])
        print("    Driver: ", adapter.get("DriverVersion") or "unavailable")

    return adapters


def choose_adapter():
    adapters = display_adapters()

    if not adapters:
        return None

    value = input("\nAdapter number, or Enter to cancel: ").strip()

    if not value:
        return None

    if not value.isdigit() or not 1 <= int(value) <= len(adapters):
        raise ValueError("Invalid adapter number.")

    return adapters[int(value) - 1]


def show_debug():
    print(
        "\nNOT VERIFIED does not establish the exact cause.\n"
        "- Check the selected adapter and installed driver version.\n"
        "- Inspect Windows Wi-Fi random-address settings separately.\n"
        "- The driver may not support a custom NetworkAddress override.\n"
        "- A registry write is not proof of a network-level change.\n"
        "- No kernel, PnP, or vendor-OUI workaround is included.\n"
        "- Do not disable Windows security protections for this tool.\n"
        "- Keep original-setting backups private and intact.\n"
        "- If a restart fails, inspect adapter status locally.\n"
        "- Test one adapter at a time; retain another way to connect.\n"
    )


def interactive():
    while True:
        print(BANNER)
        print(
            f"  v{VERSION} | Admin: {'YES' if is_admin() else 'NO'}"
            " | No kernel driver"
        )
        print(
            "\n  1  List adapters"
            "\n  2  Set random local MAC"
            "\n  3  Set custom local MAC"
            "\n  4  Restore original configuration"
            "\n  D  Debug tips"
            "\n  0  Exit"
        )

        choice = input("\n> ").strip().lower()

        if choice == "0":
            print("Goodbye.")
            return 0

        try:
            if choice == "1":
                display_adapters()

            elif choice in {"2", "3", "4"}:
                require_admin()
                adapter = choose_adapter()

                if adapter:
                    target = canonical_guid(adapter["InterfaceGuid"])

                    if choice == "2":
                        apply_mac(target, random_mac())

                    elif choice == "3":
                        value = input(
                            "New local MAC (example 02:11:22:33:44:55): "
                        )
                        apply_mac(target, value)

                    else:
                        restore_mac(target)

            elif choice == "d":
                show_debug()

            else:
                print("Choose a listed option.")

        except (Exception, KeyboardInterrupt) as error:
            print("\nERROR:", error or "Interrupted.")

        input("\nPress Enter to continue...")


def main():
    parser = argparse.ArgumentParser(
        description="Cold Mac: driver-dependent address configuration."
    )
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command")

    commands.add_parser("list", help="List physical adapters")
    commands.add_parser("menu", help="Open interactive menu")

    set_parser = commands.add_parser("set", help="Attempt an address override")
    set_parser.add_argument("adapter", help="Exact name or GUID")
    selection = set_parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--random", action="store_true")
    selection.add_argument("--mac")
    set_parser.add_argument(
        "--yes", action="store_true",
        help="Explicitly accept adapter disconnection without a prompt",
    )

    restore_parser = commands.add_parser(
        "restore", help="Restore the first saved original configuration"
    )
    restore_parser.add_argument("adapter", help="Exact name or GUID")
    restore_parser.add_argument(
        "--yes", action="store_true",
        help="Explicitly accept adapter disconnection without a prompt",
    )

    args = parser.parse_args()

    if sys.platform != "win32":
        parser.error("This application runs on Windows.")

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    try:
        if args.command in (None, "menu"):
            return interactive()

        if args.command == "list":
            display_adapters()
            return 0

        if args.command == "set":
            value = random_mac() if args.random else args.mac
            return apply_mac(args.adapter, value, args.yes)

        if args.command == "restore":
            return restore_mac(args.adapter, args.yes)

    except (Exception, KeyboardInterrupt) as error:
        print("\nERROR:", error or "Interrupted.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())