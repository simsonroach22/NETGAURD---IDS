import socket
import threading
import random
import time

target="127.0.0.1"

def flood():
    while True:
        try:
            s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            s.connect((target,80))
            s.send(b"X"*random.randint(50,5000))
            s.close()
        except:
            pass

def port_scan():
    while True:
        port=random.randint(1,1024)
        s=socket.socket()
        s.settimeout(0.1)
        try:
            s.connect((target,port))
        except:
            pass
        s.close()
        time.sleep(0.05)

def noise():
    while True:
        time.sleep(random.uniform(0.1,0.5))

print("🔥 Simulator running")

for _ in range(5):
    threading.Thread(target=flood,daemon=True).start()

for _ in range(2):
    threading.Thread(target=port_scan,daemon=True).start()

noise()
