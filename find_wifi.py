from scapy.all import get_if_list
import subprocess

result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], 
                      capture_output=True, text=True)
print(result.stdout)

print("\nNow testing each interface for packets (3 seconds each)...")
print("Keep Fing scanning on your phone!\n")

from scapy.all import sniff, IP

for iface in get_if_list():
    try:
        pkts = sniff(filter='ip', timeout=3, iface=iface)
        if len(pkts) > 0:
            print(f"FOUND PACKETS on: {iface}")
            print(f"  Captured: {len(pkts)} packets")
            for p in pkts[:3]:
                if p.haslayer(IP):
                    print(f"  {p[IP].src} -> {p[IP].dst}")
        else:
            print(f"  No packets: {iface}")
    except Exception as e:
        print(f"  Error on {iface}: {e}")
