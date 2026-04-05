from scapy.all import sniff, ICMP

print("Listening for ICMP...")

def test(p):
    if p.haslayer(ICMP):
        print("🔥 ICMP DETECTED")

sniff(prn=test, store=0)
