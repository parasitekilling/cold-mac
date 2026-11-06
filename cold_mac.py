#!/usr/bin/env python3
"""Cold Mac - Windows 11 MAC address changer."""

import argparse
import csv
import ctypes
import io
import json
import os
import random
import subprocess
import sys
import time
import winreg
from datetime import datetime, timezone

__version__ = "1.1.0"

CLASS_KEY = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
CONN_KEY = r"SYSTEM\CurrentControlSet\Control\Network\{4d36e972-e325-11ce-bfc1-08002be10318}"
HEX = "0123456789ABCDEF"
TASK_NAME = "ColdMac-Boot"

# Curated vendor OUIs (first three octets). Extend with more from the IEEE
# OUI registry as needed. Format: (vendor name, hex prefix, <= 6 hex digits).
VENDOR_OUI = (
    ("Intel",     "001B21"),
    ("Intel",     "3C970E"),
    ("Intel",     "8C1645"),
    ("Intel",     "94659C"),
    ("Realtek",   "00E04C"),
    ("Realtek",   "001CF0"),
    ("Broadcom",  "001018"),
    ("Broadcom",  "000AF7"),
    ("Apple",     "001B63"),
    ("Apple",     "3C0754"),
    ("Apple",     "A483E7"),
    ("Dell",      "001422"),
    ("Dell",      "B82A72"),
    ("HP",        "001F29"),
    ("HP",        "3CD92B"),
    ("Lenovo",    "001255"),
    ("Lenovo",    "E48D8C"),
    ("ASUS",      "001BFC"),
    ("ASUS",      "2C56DC"),
    ("TP-Link",   "001D0F"),
    ("TP-Link",   "50C7BF"),
    ("Netgear",   "00146C"),
    ("Netgear",   "204E7F"),
    ("Samsung",   "001599"),
    ("Samsung",   "5C0A5B"),
    ("Microsoft", "7C1E52"),
    ("Qualcomm",  "001374"),
    ("Qualcomm",  "04F021"),
)

EXCLUDE_MARKERS = (
    "wan miniport",
    "wi-fi direct",
    "kernel debug",
    "hyper-v",
    "virtual",
    "tap-windows",
    "openvpn",
    "wireguard",
    "bluetooth device",
    "ras async",
    "isatap",
    "teredo",
    "loopback",
    "npcap",
    "pseudo",
)


# ---------------------------------------------------------------- helpers

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run(args, timeout=30):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except Exception:
        return -1, "", ""


def read_reg(key, name):
    try:
        return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


def config_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
    return os.path.join(base, "ColdMac")


def config_path():
    return os.path.join(config_dir(), "config.json")


def load_config():
    default = {"version": 1, "interfaces": {}, "boot": False}
    p = config_path()
    if not os.path.exists(p):
        return default
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return default
    data.setdefault("version", 1)
    data.setdefault("interfaces", {})
    data.setdefault("boot", False)
    return data


def save_config(data):
    d = config_dir()
    os.makedirs(d, exist_ok=True)
    p = config_path()
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, p)


def normalize_mac(s):
    if not s:
        return None
    mac = s.replace("-", "").replace(":", "").replace(".", "").upper()
    if len(mac) != 12 or any(c not in HEX for c in mac):
        return None
    if int(mac[0:2], 16) & 0x01:
        return None
    return mac


def random_vendor_mac(vendor=None):
    pool = VENDOR_OUI
    if vendor:
        pool = tuple(v for v in VENDOR_OUI if v[0].lower() == vendor.lower())
        if not pool:
            raise ValueError(f"unknown vendor '{vendor}'")
    name, prefix = random.choice(pool)
    remaining = 12 - len(prefix)
    suffix = "".join(f"{random.randint(0, 255):02X}" for _ in range(remaining // 2))
    mac = (prefix + suffix).upper()
    first = int(mac[0:2], 16) & 0xFE
    return f"{first:02X}{mac[2:]}", name


# ---------------------------------------------------------------- registry

def friendly_name(guid):
    path = f"{CONN_KEY}\\{guid}\\Connection"
    try:
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
    except OSError:
        return None
    try:
        return winreg.QueryValueEx(k, "Name")[0]
    except OSError:
        return None
    finally:
        winreg.CloseKey(k)


def is_virtual(desc):
    d = desc.lower()
    return any(m in d for m in EXCLUDE_MARKERS)


def list_adapters(include_virtual=False):
    out = []
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, CLASS_KEY)
    except OSError:
        return out
    try:
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(root, i)
            except OSError:
                break
            i += 1
            if not sub.isdigit():
                continue
            try:
                sk = winreg.OpenKey(root, sub)
            except OSError:
                continue
            try:
                desc = read_reg(sk, "DriverDesc")
                guid = read_reg(sk, "NetCfgInstanceId")
                custom = read_reg(sk, "NetworkAddress")
            finally:
                winreg.CloseKey(sk)
            if not desc or not guid:
                continue
            if not include_virtual and is_virtual(desc):
                continue
            name = friendly_name(guid)
            if not name:
                continue
            out.append({
                "subkey": sub,
                "name": name,
                "desc": desc,
                "guid": guid,
                "custom": custom,
            })
    finally:
        winreg.CloseKey(root)
    return out


def write_custom(subkey, mac):
    path = f"{CLASS_KEY}\\{subkey}"
    try:
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE)
    except OSError:
        return False
    try:
        winreg.SetValueEx(k, "NetworkAddress", 0, winreg.REG_SZ, mac)
        return True
    except OSError:
        return False
    finally:
        winreg.CloseKey(k)


def clear_custom(subkey):
    path = f"{CLASS_KEY}\\{subkey}"
    try:
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE)
    except OSError:
        return False
    try:
        winreg.DeleteValue(k, "NetworkAddress")
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False
    finally:
        winreg.CloseKey(k)


def current_mac(name):
    code, out, _ = run(["getmac", "/v", "/fo", "csv", "/nh"])
    if code != 0 or not out:
        return None
    try:
        for row in csv.reader(io.StringIO(out)):
            if len(row) >= 3 and row[0].strip().lower() == name.lower():
                mac = row[2].replace("-", "").replace(":", "").upper()
                if len(mac) == 12 and all(c in HEX for c in mac):
                    return mac
    except Exception:
        pass
    return None


def bounce(name):
    for attempt in range(2):
        run(["netsh", "interface", "set", "interface", name, "admin=disable"])
        time.sleep(2 + attempt)
        run(["netsh", "interface", "set", "interface", name, "admin=enable"])
        time.sleep(2 + attempt)


def find(adapters, query):
    q = query.lower()
    for a in adapters:
        if a["name"].lower() == q:
            return a
    for a in adapters:
        if q in a["name"].lower() or q in a["desc"].lower():
            return a
    return None


# ---------------------------------------------------------------- commands

def do_list(include_virtual=False):
    adapters = list_adapters(include_virtual=include_virtual)
    if not adapters:
        print("no adapters found")
        return 0
    cfg = load_config()
    print(f"{'NAME':<24}{'CURRENT':<16}{'CUSTOM':<16}{'VENDOR':<12}DESCRIPTION")
    print("-" * 110)
    for ad in adapters:
        cur = current_mac(ad["name"]) or "not present"
        saved = cfg["interfaces"].get(ad["guid"], {})
        cust = saved.get("mac") or ad["custom"] or "-"
        vendor = saved.get("vendor", "-")
        print(f"{ad['name']:<24}{cur:<16}{cust:<16}{vendor:<12}{ad['desc']}")
    print()
    print("CURRENT = what getmac reports (may hide a successful spoof on some drivers)")
    print("CUSTOM  = what Cold Mac wrote to the registry for this adapter")
    if not include_virtual:
        print("(virtual adapters hidden; use --all to include them)")
    return 0


def do_apply(ad, mac, vendor):
    if not write_custom(ad["subkey"], mac):
        print("error: could not write registry value")
        return 1
    bounce(ad["name"])
    time.sleep(1)
    reported = current_mac(ad["name"])
    print(f"applied {mac} ({vendor}) to {ad['name']}")
    if reported is None:
        print("note: adapter not reported by getmac after bounce; check Device Manager")
    elif reported != mac:
        print(f"note: getmac reports {reported}. Some drivers hide the custom MAC")
        print("      from local tools; check Device Manager > adapter > Advanced")
    cfg = load_config()
    cfg["interfaces"][ad["guid"]] = {
        "name": ad["name"],
        "desc": ad["desc"],
        "mac": mac,
        "vendor": vendor,
        "set_at": datetime.now(timezone.utc).isoformat(),
    }
    save_config(cfg)
    return 0


def do_revert(ad):
    ok = clear_custom(ad["subkey"])
    cfg = load_config()
    cfg["interfaces"].pop(ad["guid"], None)
    save_config(cfg)
    if ok:
        bounce(ad["name"])
        print(f"reverted {ad['name']} to hardware MAC")
    else:
        print(f"no custom MAC set on {ad['name']}")
    return 0


def restore_all():
    cfg = load_config()
    if not cfg["interfaces"]:
        print("nothing to restore")
        return 0
    adapters = list_adapters(include_virtual=True)
    by_guid = {ad["guid"]: ad for ad in adapters}
    count = 0
    for guid in list(cfg["interfaces"].keys()):
        ad = by_guid.get(guid)
        if not ad:
            print(f"skip: adapter {guid} not present")
            cfg["interfaces"].pop(guid, None)
            continue
        if clear_custom(ad["subkey"]):
            bounce(ad["name"])
            print(f"reverted {ad['name']}")
            count += 1
        cfg["interfaces"].pop(guid, None)
    save_config(cfg)
    print(f"restored {count} adapter(s)")
    return 0


def apply_saved():
    cfg = load_config()
    if not cfg["interfaces"]:
        return 0
    adapters = list_adapters(include_virtual=True)
    by_guid = {ad["guid"]: ad for ad in adapters}
    for guid, entry in list(cfg["interfaces"].items()):
        ad = by_guid.get(guid)
        if not ad:
            continue
        if not write_custom(ad["subkey"], entry["mac"]):
            continue
        bounce(ad["name"])
    return 0


def boot_task_path():
    return os.path.join(config_dir(), "boot_task.bat")


def register_boot():
    d = config_dir()
    os.makedirs(d, exist_ok=True)
    bat = boot_task_path()
    py = sys.executable
    script = os.path.abspath(__file__)
    with open(bat, "w", encoding="utf-8", newline="") as f:
        f.write('@echo off\r\n')
        f.write(f'"{py}" "{script}" --apply-saved\r\n')
    code, _, err = run([
        "schtasks", "/Create", "/TN", TASK_NAME,
        "/TR", f'"{bat}"',
        "/SC", "ONLOGON",
        "/RL", "HIGHEST",
        "/F",
    ])
    if code != 0:
        print(f"error: schtasks failed: {err.strip()}")
        return False
    cfg = load_config()
    cfg["boot"] = True
    save_config(cfg)
    print(f"registered boot task {TASK_NAME}")
    return True


def unregister_boot():
    code, _, _ = run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    cfg = load_config()
    cfg["boot"] = False
    save_config(cfg)
    print("removed boot task" if code == 0 else "boot task not present")
    return True


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(prog="cold-mac", description="Windows 11 MAC address changer.")
    p.add_argument("--version", action="version", version=f"cold-mac {__version__}")
    p.add_argument("-l", "--list", action="store_true", help="list network adapters")
    p.add_argument("--all", action="store_true", help="include virtual adapters in --list")
    p.add_argument("-i", "--interface", help="adapter friendly name, e.g. 'Wi-Fi'")
    p.add_argument("-r", "--random", action="store_true", help="assign a random vendor MAC")
    p.add_argument("-m", "--mac", help="assign a specific 12-hex-digit MAC")
    p.add_argument("-v", "--vendor", help="restrict --random to a vendor")
    p.add_argument("--revert", action="store_true", help="restore hardware MAC for one adapter")
    p.add_argument("--restore-all", action="store_true", help="revert every adapter in config")
    p.add_argument("--apply-saved", action="store_true", help="re-apply saved MACs (boot task)")
    p.add_argument("--boot", action="store_true", help="register logon task")
    p.add_argument("--no-boot", action="store_true", help="remove logon task")
    a = p.parse_args()

    if a.list:
        return do_list(include_virtual=a.all)

    if not is_admin():
        print("error: administrator privileges required")
        return 1

    if a.boot:
        return 0 if register_boot() else 1
    if a.no_boot:
        return 0 if unregister_boot() else 1
    if a.apply_saved:
        return apply_saved()
    if a.restore_all:
        return restore_all()

    if not a.interface:
        print("error: --interface required (use --list to see names)")
        return 1

    adapters = list_adapters(include_virtual=True)
    ad = find(adapters, a.interface)
    if not ad:
        print(f"error: adapter '{a.interface}' not found")
        return 1

    if a.revert:
        return do_revert(ad)

    if a.random:
        try:
            mac, vendor = random_vendor_mac(a.vendor)
        except ValueError as e:
            print(f"error: {e}")
            return 1
        return do_apply(ad, mac, vendor)

    if a.mac:
        mac = normalize_mac(a.mac)
        if not mac:
            print("error: --mac must be 12 hex digits, unicast (first byte even)")
            return 1
        return do_apply(ad, mac, "custom")

    print("error: specify --random, --mac, --revert, or --restore-all")
    return 1


if __name__ == "__main__":
    sys.exit(main())