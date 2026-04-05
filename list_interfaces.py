from scapy.all import get_if_list, conf
print("Available interfaces:")
for i, iface in enumerate(get_if_list()):
    print(f"  [{i}] {iface}")
print(f"\nDefault interface: {conf.iface}")
