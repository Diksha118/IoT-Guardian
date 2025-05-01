import subprocess
import re
import socket
import platform
from typing import List, Dict
from database import get_device_info, get_all_devices

def get_connected_devices() -> List[Dict]:
    """Get devices connected to the hotspot (MacOS + ARP parsing)."""
    devices = []

    # Method 1: Parse macOS DHCP leases
    try:
        with open("/var/db/dhcpd_leases", "r") as f:
            content = f.read()
            for entry in content.split("}"):
                if "ip_address" in entry:
                    ip = re.search(r"ip_address=([\d.]+)", entry)
                    mac = re.search(r"hw_address=\d+,?([0-9a-fA-F:]+)", entry)
                    hostname = re.search(r"hostname=([^\s]+)", entry)
                    print("Parsed DHCP:", ip.group(1), mac.group(1))
                    if ip and mac:
                        devices.append({
                            "ipv4": ip.group(1),
                            "mac": format_mac(mac.group(1)),
                            "name": hostname.group(1) if hostname else "DHCP Client",
                            "source": "dhcp"
                        })
    except Exception as e:
        print(f"DHCP lease error: {e}")

    # Method 2: Parse ARP table
    try:
        arp_command = "arp -a -i bridge100" if platform.system() == "Darwin" else "arp -a"
        output = subprocess.check_output(arp_command, shell=True, text=True)

        for line in output.splitlines():
            match = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([0-9a-fA-F:]{17})", line)
            if match and "incomplete" not in line.lower() and "permanent" not in line.lower():
                ip = match.group(1)
                mac = format_mac(match.group(2))

                if ip in ("169.254.255.255", "192.168.2.255", "224.0.0.251", "239.255.255.250"):
                    continue

                # Only add if not already present
                if not any(d.get("mac") == mac for d in devices):
                    devices.append({
                        "ipv4": ip,
                        "mac": mac,
                        "name": f"Device-{ip.split('.')[-1]}",
                        "source": "arp"
                    })
    except Exception as e:
        print(f"ARP scan error: {e}")

    # Method 3: Try hostname resolution
    for device in devices:
        if "ipv4" in device and (not device.get("name") or device["name"] in ["DHCP Client", ""]):
            try:
                device["name"] = socket.gethostbyaddr(device["ipv4"])[0].split('.')[0]
            except:
                device["name"] = f"Device-{device['ipv4'].split('.')[-1]}"

    # Add vendor + status
    final_devices = []
    seen_macs = set()
    for device in devices:
        if device["mac"] not in seen_macs:
            device["vendor"] = get_vendor_from_mac(device["mac"])
            device["status"] = "Connected"
            seen_macs.add(device["mac"])
            final_devices.append(device)

    # Merge with database info
    db_devices = {d['mac']: d for d in get_all_devices()}
    for device in final_devices:
        if device['mac'] in db_devices:
            db_info = db_devices[device['mac']]
            device.update({
                'name': db_info.get('name', device.get('name')),
                'model': db_info.get('model', ''),
                'version': db_info.get('version', ''),
                'description': db_info.get('description', '')
            })

    return final_devices

def format_mac(mac: str) -> str:
    """Format MAC address as aa:bb:cc:dd:ee:ff"""
    mac = mac.lower().replace("-", ":").replace(".", ":").replace(",", ":")
    if len(mac) == 17:
        return mac
    if len(mac) == 12:
        return ":".join([mac[i:i+2] for i in range(0, 12, 2)])
    return mac

def get_vendor_from_mac(mac: str) -> str:
    """Lookup vendor based on MAC OUI"""
    oui = mac[:8].lower()

    if oui in ("00:1a:79", "fc:9c:a7", "ac:bc:32", "10:9a:dd", 
               "7c:6d:62", "7c:04:d0", "7c:6a:60", "7c:38:ad"):
        return "Apple"

    oui_db = {
        "c6:35:d9": "Apple",
        "ce:9f:49": "Unknown Device",
        "fe:9c:a7": "Apple",
        "b8:27:eb": "Raspberry Pi",
        "dc:a6:32": "Raspberry Pi",
        "00:0c:29": "VMware",
        "00:50:56": "VMware",
        "00:1d:60": "Sony",
        "00:23:12": "Intel",
        "a4:c1:38": "Samsung",
        "00:14:a4": "TP-Link",
        "00:18:82": "D-Link",
        "00:19:5b": "Netgear",
        "00:21:5a": "Samsung",
        "00:24:01": "Huawei",
        "00:26:4b": "Amazon",
    }
    return oui_db.get(oui, "Unknown")