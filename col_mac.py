#!/usr/bin/env python3
"""Cold Mac - Windows 11 MAC address changer."""

import argparse
import ctypes
import csv
import io
import random
import subprocess
import sys
import time
import winreg

CLASS_KEY = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"
CONN_KEY = r"SYSTEM\CurrentControlSet\Control\Network\{4d36e972-e325-11ce-bfc1-08002be10318}"
HEX = "0123456789ABCDEF"


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


def list_adapters():
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


def random_mac():
    return "02" + "".join(f"{random.randint(0, 255):02X}" for _ in range(5))


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


def bounce(name):
    run(["netsh", "interface", "set", "interface", name, "admin=disable"])
    time.sleep(2)
    run(["netsh", "interface", "set", "interface", name, "admin=enable"])
    time.sleep(2)


def find(adapters, query):
    q = query.lower()
    for a in adapters:
        if a["name"].lower() == q:
            return a
    for a in adapters:
        if q in a["name"].lower() or q in a["desc"].lower():
            return a
    return None


def main():
    p = argparse.ArgumentParser(prog="cold-mac")
    p.add_argument("-l", "--list", action="store_true")
    p.add_argument("-i", "--interface")
    p.add_argument("-r", "--random", action="store_true")
    p.add_argument("-m", "--mac")
    p.add_argument("--revert", action="store_true")
    a = p.parse_args()

    if not is_admin():
        print("error: administrator privileges required")
        return 1

    adapters = list_adapters()

    if a.list:
        if not adapters:
            print("no adapters found")
            return 0
        print(f"{'NAME':<24}{'CURRENT':<16}{'CUSTOM':<14}DESCRIPTION")
        print("-" * 100)
        for ad in adapters:
            cur = current_mac(ad["name"]) or "unknown"
            cust = ad["custom"] or "-"
            print(f"{ad['name']:<24}{cur:<16}{cust:<14}{ad['desc']}")
        return 0

    if not a.interface:
        print("error: --interface required (use --list)")
        return 1

    ad = find(adapters, a.interface)
    if not ad:
        print(f"error: adapter '{a.interface}' not found")
        return 1

    if a.revert:
        if clear_custom(ad["subkey"]):
            bounce(ad["name"])
            print(f"reverted {ad['name']} to hardware MAC")
        else:
            print(f"no custom MAC set on {ad['name']}")
        return 0

    if a.random:
        mac = random_mac()
    elif a.mac:
        mac = a.mac.replace("-", "").replace(":", "").upper()
        if len(mac) != 12 or any(c not in HEX for c in mac):
            print("error: MAC must be 12 hex digits")
            return 1
        if int(mac[0:2], 16) & 0x01:
            print("error: multicast bit set; MAC must be unicast")
            return 1
    else:
        print("error: specify --random, --mac, or --revert")
        return 1

    if not write_custom(ad["subkey"], mac):
        print("error: could not write registry value")
        return 1

    bounce(ad["name"])
    time.sleep(1)
    verify = current_mac(ad["name"])
    if verify and verify != mac:
        print(f"warning: adapter reports {verify} (expected {mac})")
        print("the driver may ignore this value; use --revert to clean up")
        return 2

    print(f"applied {mac} to {ad['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())