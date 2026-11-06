#!/usr/bin/env python3
"""Cold Mac 1.1.1 - Interactive Windows 11 MAC & Telemetry Spoofer."""

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

__version__ = "1.1.1"

BANNER = r"""
 ██████╗ ██████╗ ██╗     ██████╗     ███╗   ███╗ █████╗  ██████╗ 
██╔════╝██╔═══██╗██║     ██╔══██╗    ████╗ ████║██╔══██╗██╔════╝ 
██║     ██║   ██║██║     ██║  ██║    ██╔████╔██║███████║██║      
██║     ██║   ██║██║     ██║  ██║    ██║╚██╔╝██║██╔══██║██║      
╚██████╗╚██████╔╝███████╗██████╔╝    ██║ ╚═╝ ██║██║  ██║╚██████╗ 
 ╚═════╝ ╚═════╝ ╚══════╝╚═════╝     ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ 
        C O L D R O O M   //   by parasitekilling
"""

CLASS_KEY = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
CONN_KEY = r"SYSTEM\CurrentControlSet\Control\Network\{4d36e972-e325-11ce-bfc1-08002be10318}"
HEX = "0123456789ABCDEF"
TASK_NAME = "ColdMac-Boot"

VENDOR_OUI = (
    ("Intel",     "001B21"), ("Intel",     "3C970E"), ("Intel",     "8C1645"),
    ("Intel",     "94659C"), ("Intel",     "C8E2EB"),
    ("Realtek",   "00E04C"), ("Realtek",   "001CF0"), ("Realtek",   "00C0CA"),
    ("Realtek",   "52540A"),
    ("Broadcom",  "001018"), ("Broadcom",  "000AF7"),
    ("Apple",     "001B63"), ("Apple",     "3C0754"), ("Apple",     "A483E7"),
    ("Dell",      "001422"), ("Dell",      "B82A72"),
    ("HP",        "001F29"), ("HP",        "3CD92B"),
    ("Lenovo",    "001255"), ("Lenovo",    "E48D8C"),
    ("ASUS",      "001BFC"), ("ASUS",      "2C56DC"),
    ("TP-Link",   "001D0F"), ("TP-Link",   "50C7BF"),
    ("Netgear",   "00146C"), ("Netgear",   "204E7F"),
    ("Samsung",   "001599"), ("Samsung",   "5C0A5B"),
    ("Microsoft", "7C1E52"),
    ("Qualcomm",  "001374"), ("Qualcomm",  "04F021"),
)

EXCLUDE_MARKERS = (
    "wan miniport", "wi-fi direct", "kernel debug", "hyper-v", "virtual",
    "tap-windows", "openvpn", "wireguard", "bluetooth device", "ras async",
    "isatap", "teredo", "loopback", "npcap", "pseudo", "wintun",
    "remote ndis", "internet sharing", "userspace tunnel",
)

# ──────────────────────────────────────────────────────────────── logging

def enable_vt():
    try:
        k32 = ctypes.windll.kernel32
        handle = k32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not k32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(k32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"
    BRED = "\033[91m"
    BGREEN = "\033[92m"
    BYELLOW = "\033[93m"
    BBLUE = "\033[94m"
    BMAGENTA = "\033[95m"
    BCYAN = "\033[96m"


_COLOR = False


def set_color(enabled):
    global _COLOR
    _COLOR = enabled


def paint(s, color):
    if not _COLOR:
        return s
    return f"{color}{s}{C.RESET}"


def log(level, msg):
    tag = {
        "info": ("[*]", C.CYAN),
        "ok":   ("[+]", C.BGREEN),
        "warn": ("[!]", C.BYELLOW),
        "err":  ("[-]", C.BRED),
        "dbg":  ("[~]", C.GRAY),
    }[level]
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{paint(tag[0], tag[1])} {paint(ts, C.DIM)} {msg}")


# ──────────────────────────────────────────────────────────────── helpers

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


def write_reg(key, name, value, vtype=winreg.REG_SZ):
    try:
        winreg.SetValueEx(key, name, 0, vtype, value)
        return True
    except OSError:
        return False


def delete_reg(key, name):
    try:
        winreg.DeleteValue(key, name)
        return True
    except (FileNotFoundError, OSError):
        return False


def config_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser(r"~\AppData\Local")
    return os.path.join(base, "ColdMac")


def config_path():
    return os.path.join(config_dir(), "config.json")


def load_config():
    default = {"version": 2, "interfaces": {}, "boot": False, "telemetry_backup": {}}
    p = config_path()
    if not os.path.exists(p):
        return default
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return default
    data.setdefault("version", 2)
    data.setdefault("interfaces", {})
    data.setdefault("boot", False)
    data.setdefault("telemetry_backup", {})
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


def oui_match(mac):
    if not mac or len(mac) < 6:
        return None
    prefix = mac[0:6].upper()
    for name, oui in VENDOR_OUI:
        if oui.upper() == prefix:
            return name
    return None


# ──────────────────────────────────────────────────────────────── registry

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
                pnp = read_reg(sk, "PnPCapabilities")
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
                "subkey": sub, "name": name, "desc": desc,
                "guid": guid, "custom": custom, "pnp": pnp,
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
    except (FileNotFoundError, OSError):
        return False
    finally:
        winreg.CloseKey(k)


def set_pnp_fix(subkey, enable=True):
    path = f"{CLASS_KEY}\\{subkey}"
    try:
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE)
    except OSError:
        return False
    try:
        if enable:
            winreg.SetValueEx(k, "PnPCapabilities", 0, winreg.REG_DWORD, 24)
        else:
            try:
                winreg.DeleteValue(k, "PnPCapabilities")
            except FileNotFoundError:
                pass
        return True
    except OSError:
        return False
    finally:
        winreg.CloseKey(k)


def set_telemetry(subkey, guid, driver_desc=None, friendly=None):
    """Change DriverDesc and/or friendly name. Returns (ok, old_values)."""
    old = {}
    ok = True

    if driver_desc is not None:
        path = f"{CLASS_KEY}\\{subkey}"
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_READ)
        except OSError:
            return False, old
        try:
            old["driver_desc"] = read_reg(k, "DriverDesc")
            if not write_reg(k, "DriverDesc", driver_desc):
                ok = False
        finally:
            winreg.CloseKey(k)

    if friendly is not None:
        path = f"{CONN_KEY}\\{guid}\\Connection"
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE | winreg.KEY_READ)
        except OSError:
            return False, old
        try:
            old["friendly"] = read_reg(k, "Name")
            if not write_reg(k, "Name", friendly):
                ok = False
        finally:
            winreg.CloseKey(k)

    return ok, old


def restore_telemetry(subkey, guid, backup):
    ok = True
    if "driver_desc" in backup and backup["driver_desc"] is not None:
        path = f"{CLASS_KEY}\\{subkey}"
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, "DriverDesc", 0, winreg.REG_SZ, backup["driver_desc"])
            winreg.CloseKey(k)
        except OSError:
            ok = False
    if "friendly" in backup and backup["friendly"] is not None:
        path = f"{CONN_KEY}\\{guid}\\Connection"
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, "Name", 0, winreg.REG_SZ, backup["friendly"])
            winreg.CloseKey(k)
        except OSError:
            ok = False
    return ok


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


def bounce(name, verbose=True):
    if verbose:
        log("info", f"Disabling adapter '{name}'...")
    run(["netsh", "interface", "set", "interface", name, "admin=disable"])
    time.sleep(2)
    if verbose:
        log("info", f"Re-enabling adapter '{name}'...")
    run(["netsh", "interface", "set", "interface", name, "admin=enable"])
    time.sleep(2)
    if verbose:
        log("ok", f"Adapter '{name}' restarted.")


def find(adapters, query):
    q = query.lower()
    for a in adapters:
        if a["name"].lower() == q:
            return a
    for a in adapters:
        if q in a["name"].lower() or q in a["desc"].lower():
            return a
    return None


# ──────────────────────────────────────────────────────────────── classify

def classify(ad, current, config_entry):
    if not current:
        return "ABSENT", C.GRAY
    cur = current.upper()
    cust = ad.get("custom")
    if cust and cust.upper() == cur:
        return "SPOOFED", C.BYELLOW
    if cust and cust.upper() != cur:
        return "IGNORED", C.BRED
    try:
        first = int(cur[0:2], 16)
    except (ValueError, IndexError):
        return "UNKNOWN", C.DIM
    if first & 0x02:
        return "LOCAL", C.BRED
    return "REAL", C.BBLUE


# ──────────────────────────────────────────────────────────────── pnp fix

def do_pnp_fix(ad):
    log("info", f"Writing PnPCapabilities=24 to {ad['desc']}...")
    if set_pnp_fix(ad["subkey"], True):
        log("ok", "PnPCapabilities set. This disables NIC power management.")
        log("warn", "The adapter may run slightly warmer and use more battery.")
        bounce(ad["name"])
        return True
    log("err", "Failed to write PnPCapabilities. Are you admin?")
    return False


def do_pnp_remove(ad):
    if set_pnp_fix(ad["subkey"], False):
        log("ok", "PnPCapabilities removed. Power management restored.")
        bounce(ad["name"])
        return True
    log("err", "Failed to remove PnPCapabilities.")
    return False


# ──────────────────────────────────────────────────────────────── apply

def apply_mac(ad, mac, vendor, verbose=True):
    if verbose:
        log("info", f"Writing MAC {mac} ({vendor}) to {ad['desc']}...")
    if not write_custom(ad["subkey"], mac):
        log("err", "Failed to write NetworkAddress. Run as Administrator.")
        return False
    if verbose:
        log("ok", "Registry value written.")
    bounce(ad["name"], verbose=verbose)
    time.sleep(1)

    reported = current_mac(ad["name"])
    if verbose:
        log("info", f"getmac reports: {reported or 'not present'}")
    if reported and reported.upper() == mac.upper():
        log("ok", "Spoof confirmed at getmac level.")
    elif reported:
        log("warn", "getmac still reports the old MAC.")
        log("info", "This is expected on some drivers. The spoof may still work at the wire level.")
        log("info", "Run 'Debug tips' from the menu for verification steps.")

    cfg = load_config()
    cfg["interfaces"][ad["guid"]] = {
        "name": ad["name"], "desc": ad["desc"], "mac": mac,
        "vendor": vendor, "set_at": datetime.now(timezone.utc).isoformat(),
    }
    save_config(cfg)
    return True


def revert_mac(ad):
    log("info", f"Reverting {ad['name']}...")
    if not clear_custom(ad["subkey"]):
        log("warn", "No NetworkAddress value found. Nothing to revert.")
    cfg = load_config()
    cfg["interfaces"].pop(ad["guid"], None)
    save_config(cfg)
    bounce(ad["name"])
    log("ok", f"{ad['name']} reverted to hardware MAC.")
    return True


def restore_all():
    cfg = load_config()
    if not cfg["interfaces"]:
        log("warn", "Nothing to restore.")
        return
    adapters = list_adapters(include_virtual=True)
    by_guid = {a["guid"]: a for a in adapters}
    for guid in list(cfg["interfaces"].keys()):
        ad = by_guid.get(guid)
        if not ad:
            log("warn", f"Adapter {guid} not present; skipping.")
            cfg["interfaces"].pop(guid, None)
            continue
        clear_custom(ad["subkey"])
        bounce(ad["name"])
        log("ok", f"Reverted {ad['name']}.")
        cfg["interfaces"].pop(guid, None)
    save_config(cfg)


def apply_saved():
    cfg = load_config()
    if not cfg["interfaces"]:
        return
    adapters = list_adapters(include_virtual=True)
    by_guid = {a["guid"]: a for a in adapters}
    for guid, entry in list(cfg["interfaces"].items()):
        ad = by_guid.get(guid)
        if not ad:
            continue
        write_custom(ad["subkey"], entry["mac"])
        bounce(ad["name"], verbose=False)


# ──────────────────────────────────────────────────────────────── boot

def boot_task_path():
    return os.path.join(config_dir(), "boot_task.bat")


def register_boot():
    d = config_dir()
    os.makedirs(d, exist_ok=True)
    bat = boot_task_path()
    script = os.path.abspath(__file__)
    with open(bat, "w", encoding="utf-8", newline="") as f:
        f.write("@echo off\r\n")
        f.write(f'"{sys.executable}" "{script}" --apply-saved\r\n')
    code, _, err = run([
        "schtasks", "/Create", "/TN", TASK_NAME,
        "/TR", f'"{bat}"', "/SC", "ONLOGON", "/RL", "HIGHEST", "/F",
    ])
    if code != 0:
        log("err", f"schtasks failed: {err.strip()}")
        return False
    cfg = load_config()
    cfg["boot"] = True
    save_config(cfg)
    log("ok", f"Boot task '{TASK_NAME}' registered.")
    return True


def unregister_boot():
    code, _, _ = run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    cfg = load_config()
    cfg["boot"] = False
    save_config(cfg)
    log("ok" if code == 0 else "warn", "Boot task removed." if code == 0 else "Boot task not present.")
    return True


# ──────────────────────────────────────────────────────────────── UI

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def show_banner():
    if _COLOR:
        for line in BANNER.split("\n"):
            if "parasitekilling" in line:
                print(f"{C.BMAGENTA}{line}{C.RESET}")
            else:
                print(f"{C.BCYAN}{line}{C.RESET}")
    else:
        print(BANNER)
    print(paint(f"  v{__version__}  |  Admin: {'YES' if is_admin() else 'NO'}  |  Boot: {'ON' if load_config()['boot'] else 'OFF'}", C.DIM))
    print()


def adapter_table(adapters, cfg, show_index=False):
    if show_index:
        print(paint(f"  {'#':<4}{'NAME':<14}{'CURRENT':<16}{'TYPE':<10}{'VENDOR':<12}DESCRIPTION", C.BOLD))
        print(paint("  " + "-" * 108, C.DIM))
    else:
        print(paint(f"  {'NAME':<14}{'CURRENT':<16}{'TYPE':<10}{'VENDOR':<12}DESCRIPTION", C.BOLD))
        print(paint("  " + "-" * 108, C.DIM))

    for i, ad in enumerate(adapters, 1):
        cur = current_mac(ad["name"])
        cur_disp = cur or "not present"
        entry = cfg["interfaces"].get(ad["guid"], {})
        label, tcolor = classify(ad, cur, entry)
        vendor = oui_match(cur) if cur else None
        if not vendor and entry:
            vendor = entry.get("vendor")
        vendor_disp = vendor or "-"

        prefix = f"  [{i}] " if show_index else "  "
        name_pad = f"{ad['name']:<14}"
        cur_pad = paint(f"{cur_disp:<16}", tcolor)
        type_pad = paint(f"{label:<10}", tcolor)
        vendor_pad = f"{vendor_disp:<12}"
        print(f"{prefix}{name_pad}{cur_pad}{type_pad}{vendor_pad}{ad['desc']}")


def pick_adapter(adapters, cfg, prompt="  Select adapter #: "):
    adapter_table(adapters, cfg, show_index=True)
    while True:
        try:
            choice = input(prompt).strip()
            if not choice:
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(adapters):
                return adapters[idx]
            print("  Invalid number.")
        except (ValueError, KeyboardInterrupt):
            return None


def show_status(cfg):
    adapters = list_adapters(include_virtual=False)
    spoofed = sum(1 for ad in adapters if ad.get("custom"))
    print(paint(f"  Coldroom status: {len(adapters)} adapter(s), {spoofed} spoofed, boot {'ON' if cfg['boot'] else 'OFF'}", C.DIM))
    print()


def show_menu():
    print(paint("  ┌─────────────────────────────────────────────────────────────┐", C.CYAN))
    print(paint("  │  1  List adapters                                           │", C.CYAN))
    print(paint("  │  2  Quick spoof (auto PnP fix + random MAC)                 │", C.CYAN))
    print(paint("  │  3  Randomize MAC (choose vendor)                           │", C.CYAN))
    print(paint("  │  4  Set custom MAC                                          │", C.CYAN))
    print(paint("  │  5  Revert MAC (single adapter)                             │", C.CYAN))
    print(paint("  │  6  Revert all adapters                                     │", C.CYAN))
    print(paint("  │  7  Advanced: PnP fix (Realtek/Intel stuck-MAC fix)         │", C.CYAN))
    print(paint("  │  8  Advanced: Spoof telemetry (name/description)            │", C.CYAN))
    print(paint("  │  9  Toggle boot persistence                                 │", C.CYAN))
    print(paint("  │  D  Debug tips (MAC not changing?)                          │", C.CYAN))
    print(paint("  │  C  Show config                                             │", C.CYAN))
    print(paint("  │  0  Exit                                                    │", C.CYAN))
    print(paint("  └─────────────────────────────────────────────────────────────┘", C.CYAN))


def debug_tips():
    clear()
    show_banner()
    print(paint("  DEBUG TIPS — MAC not changing?\n", C.BOLD))
    tips = [
        ("getmac still shows old MAC",
         "This is normal on many drivers. getmac/ipconfig read the firmware MAC.\n"
         "The spoof is still active at the wire level. Verify from another device:\n"
         "  arp -a | findstr <your-ip>\n"
         "or check your router's connected-devices page."),
        ("Device Manager shows old MAC",
         "Open Device Manager > Network adapters > your adapter > Properties >\n"
         "Advanced > Network Address. If the field is empty, the driver rejected it.\n"
         "Run 'Advanced: PnP fix' from the menu, then retry."),
        ("PnP fix didn't help",
         "Some drivers (Realtek RTL8822BE, MediaTek MT7921) lock MAC at firmware\n"
         "level. Update or roll back the driver, or use the vendor's own utility."),
        ("Adapter disappeared after spoof",
         "Some USB Wi-Fi adapters need 10-20 seconds to re-enumerate. Wait, or\n"
         "replug the adapter."),
        ("Admin required",
         "Right-click Terminal / PowerShell and choose 'Run as administrator'.\n"
         "List and debug work without admin; every write needs it."),
        ("Revert didn't stick",
         "Disable the adapter, delete NetworkAddress manually in regedit, re-enable.\n"
         "Or run 'Revert all' from the menu."),
    ]
    for title, body in tips:
        print(paint(f"  ▸ {title}", C.BYELLOW))
        for line in body.split("\n"):
            print(f"    {line}")
        print()
    input(paint("  Press Enter to return...", C.DIM))


# ──────────────────────────────────────────────────────────────── actions

def action_quick_spoof():
    adapters = list_adapters(include_virtual=False)
    if not adapters:
        log("err", "No physical adapters found.")
        return
    ad = pick_adapter(adapters, load_config())
    if not ad:
        return
    log("info", f"Target: {ad['desc']} ({ad['name']})")
    do_pnp_fix(ad)
    mac, vendor = random_vendor_mac()
    apply_mac(ad, mac, vendor)
    input(paint("\n  Press Enter to return...", C.DIM))


def action_random_mac():
    adapters = list_adapters(include_virtual=False)
    if not adapters:
        log("err", "No physical adapters found.")
        return
    ad = pick_adapter(adapters, load_config())
    if not ad:
        return

    vendors = sorted(set(v[0] for v in VENDOR_OUI))
    print(paint("\n  Vendors:", C.BOLD))
    for i, v in enumerate(vendors, 1):
        print(f"    {i:2d}. {v}")
    print("     0. Any")
    try:
        vc = input("  Choose vendor #: ").strip()
        vendor = None if vc == "0" or not vc else vendors[int(vc) - 1]
    except (ValueError, IndexError, KeyboardInterrupt):
        vendor = None

    mac, vname = random_vendor_mac(vendor)
    apply_mac(ad, mac, vname)
    input(paint("\n  Press Enter to return...", C.DIM))


def action_custom_mac():
    adapters = list_adapters(include_virtual=False)
    if not adapters:
        log("err", "No physical adapters found.")
        return
    ad = pick_adapter(adapters, load_config())
    if not ad:
        return
    raw = input("  Enter 12-hex MAC (e.g. 00E04C1A2B3C): ").strip()
    mac = normalize_mac(raw)
    if not mac:
        log("err", "Invalid MAC. Must be 12 hex digits, first byte even (unicast).")
        input(paint("\n  Press Enter to return...", C.DIM))
        return
    apply_mac(ad, mac, "custom")
    input(paint("\n  Press Enter to return...", C.DIM))


def action_revert_single():
    adapters = list_adapters(include_virtual=False)
    if not adapters:
        log("err", "No physical adapters found.")
        return
    ad = pick_adapter(adapters, load_config())
    if not ad:
        return
    revert_mac(ad)
    input(paint("\n  Press Enter to return...", C.DIM))


def action_revert_all():
    restore_all()
    input(paint("\n  Press Enter to return...", C.DIM))


def action_pnp():
    adapters = list_adapters(include_virtual=False)
    if not adapters:
        log("err", "No physical adapters found.")
        return
    ad = pick_adapter(adapters, load_config())
    if not ad:
        return
    print("\n  1. Apply PnP fix (disable power management)")
    print("  2. Remove PnP fix (restore power management)")
    c = input("  Choice [1/2]: ").strip()
    if c == "1":
        do_pnp_fix(ad)
    elif c == "2":
        do_pnp_remove(ad)
    else:
        log("warn", "Cancelled.")
    input(paint("\n  Press Enter to return...", C.DIM))


def action_telemetry():
    adapters = list_adapters(include_virtual=False)
    if not adapters:
        log("err", "No physical adapters found.")
        return
    ad = pick_adapter(adapters, load_config())
    if not ad:
        return
    cfg = load_config()
    backup = cfg["telemetry_backup"].get(ad["guid"], {})
    print(paint(f"\n  Current DriverDesc : {ad['desc']}", C.DIM))
    print(paint(f"  Current Friendly   : {ad['name']}", C.DIM))
    if backup:
        print(paint(f"  Backup available   : {backup}", C.DIM))
    print()
    print("  1. Change DriverDesc (Device Manager description)")
    print("  2. Change FriendlyName (network adapter name)")
    print("  3. Change both")
    print("  4. Restore from backup")
    c = input("  Choice [1-4]: ").strip()

    if c == "4":
        if not backup:
            log("warn", "No backup stored for this adapter.")
        else:
            restore_telemetry(ad["subkey"], ad["guid"], backup)
            cfg["telemetry_backup"].pop(ad["guid"], None)
            save_config(cfg)
            bounce(ad["name"])
            log("ok", "Telemetry restored from backup.")
        input(paint("\n  Press Enter to return...", C.DIM))
        return

    new_desc = None
    new_friendly = None
    if c in ("1", "3"):
        new_desc = input("  New DriverDesc: ").strip() or None
    if c in ("2", "3"):
        new_friendly = input("  New FriendlyName: ").strip() or None

    if new_desc is None and new_friendly is None:
        log("warn", "Nothing to change.")
        input(paint("\n  Press Enter to return...", C.DIM))
        return

    ok, old = set_telemetry(ad["subkey"], ad["guid"], new_desc, new_friendly)
    if ok:
        cfg["telemetry_backup"][ad["guid"]] = old
        save_config(cfg)
        bounce(ad["name"])
        log("ok", "Telemetry updated. Restart Device Manager to see it.")
        log("info", f"Backup stored: {old}")
    else:
        log("err", "Telemetry change failed. Admin required.")
    input(paint("\n  Press Enter to return...", C.DIM))


def action_boot():
    cfg = load_config()
    if cfg["boot"]:
        unregister_boot()
    else:
        register_boot()
    input(paint("\n  Press Enter to return...", C.DIM))


def action_config():
    clear()
    show_banner()
    cfg = load_config()
    print(paint("  Config path: " + config_path(), C.DIM))
    print(json.dumps(cfg, indent=2))
    input(paint("\n  Press Enter to return...", C.DIM))


# ──────────────────────────────────────────────────────────────── interactive

def interactive():
    while True:
        clear()
        show_banner()
        cfg = load_config()
        show_status(cfg)
        show_menu()
        choice = input(paint("  > ", C.BOLD)).strip().lower()

        if choice == "0":
            print(paint("\n  Goodbye.\n", C.CYAN))
            break
        elif choice == "1":
            clear(); show_banner()
            adapter_table(list_adapters(include_virtual=False), cfg)
            input(paint("\n  Press Enter to return...", C.DIM))
        elif choice == "2":
            action_quick_spoof()
        elif choice == "3":
            action_random_mac()
        elif choice == "4":
            action_custom_mac()
        elif choice == "5":
            action_revert_single()
        elif choice == "6":
            action_revert_all()
        elif choice == "7":
            action_pnp()
        elif choice == "8":
            action_telemetry()
        elif choice == "9":
            action_boot()
        elif choice == "d":
            debug_tips()
        elif choice == "c":
            action_config()
        else:
            log("warn", "Unknown option.")
            time.sleep(1)


# ──────────────────────────────────────────────────────────────── cli

def cli_main():
    p = argparse.ArgumentParser(prog="cold-mac", description="Windows 11 MAC & Telemetry Spoofer.")
    p.add_argument("--version", action="version", version=f"cold-mac {__version__}")
    p.add_argument("-l", "--list", action="store_true")
    p.add_argument("--all", action="store_true")
    p.add_argument("--no-color", action="store_true")
    p.add_argument("-i", "--interface")
    p.add_argument("-r", "--random", action="store_true")
    p.add_argument("-m", "--mac")
    p.add_argument("-v", "--vendor")
    p.add_argument("--revert", action="store_true")
    p.add_argument("--restore-all", action="store_true")
    p.add_argument("--apply-saved", action="store_true")
    p.add_argument("--pnp-fix", action="store_true")
    p.add_argument("--boot", action="store_true")
    p.add_argument("--no-boot", action="store_true")
    a = p.parse_args()

    set_color(not a.no_color and enable_vt())

    if a.list:
        cfg = load_config()
        adapter_table(list_adapters(include_virtual=a.all), cfg)
        return 0

    if not is_admin():
        log("err", "Administrator privileges required.")
        return 1

    if a.boot: return 0 if register_boot() else 1
    if a.no_boot: return 0 if unregister_boot() else 1
    if a.apply_saved: apply_saved(); return 0
    if a.restore_all: restore_all(); return 0

    if not a.interface:
        log("err", "--interface required (use --list)")
        return 1

    adapters = list_adapters(include_virtual=True)
    ad = find(adapters, a.interface)
    if not ad:
        log("err", f"Adapter '{a.interface}' not found.")
        return 1

    if a.revert: return 0 if revert_mac(ad) else 1
    if a.pnp_fix: return 0 if do_pnp_fix(ad) else 1

    if a.random:
        try: mac, vendor = random_vendor_mac(a.vendor)
        except ValueError as e:
            log("err", str(e)); return 1
        return 0 if apply_mac(ad, mac, vendor) else 1

    if a.mac:
        mac = normalize_mac(a.mac)
        if not mac:
            log("err", "Invalid MAC."); return 1
        return 0 if apply_mac(ad, mac, "custom") else 1

    log("err", "Specify --random, --mac, --revert, or --pnp-fix.")
    return 1


def main():
    if len(sys.argv) == 1:
        set_color(enable_vt())
        interactive()
        return 0
    return cli_main()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n")
        sys.exit(130)