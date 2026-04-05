from scapy.all import sniff, IP
print('Sniffing 10 seconds - run Fing now!')
pkts = sniff(filter='ip', timeout=10)
print(f'Captured: {len(pkts)} packets')
for p in pkts[:5]:
    if p.haslayer(IP):
        print(f'  {p[IP].src} -> {p[IP].dst}')
