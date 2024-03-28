from socket import *
import time
import threading

from encryption import encrypt, decrypt, create_key

class Messager:
    def __init__(self, addr, mask, port=9613, me=None):
        self.peers = {}
        self.me = None
        self.hello = b'Imma here!'
        self.req = b'Gimme dat!'
        self.key, self.pkey = create_key()
        self.port = port
        self.bcast = '.'.join(list(map(str, [int(a) | (255 ^ int(m)) for a, m in zip(addr.split('.'), mask.split('.'))])))
    
    
    def broadcast(self):
        while True:
            s = socket(AF_INET, SOCK_DGRAM)
            s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)   
            s.sendto(self.hello + self.pkey, (self.bcast, self.port))
            s.close()
            time.sleep(1)

    
    def request(self):
        while True:
            s = socket(AF_INET, SOCK_DGRAM)
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            prompt = input().encode('utf-8')
            for addr in self.peers:
                other_key = self.peers[addr]
                enc = encrypt(other_key, prompt)
                s.sendto(self.req + enc, (addr, self.port))
            s.close()

    
    def record(self):
        while True:
            s = socket(AF_INET, SOCK_DGRAM)
            s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.bind((self.bcast, self.port))
            data, addr = s.recvfrom(1024)
            if data[:10] == self.hello and addr[0] != self.me:
                if data[10:] == self.pkey:
                    self.me = addr[0]
                    print(f"I am existing as {self.me}")
                else:
                    self.peers[addr[0]] = data[10:]
            s.close()

    
    def receive(self):
        while True:
            if self.me:
                s = socket(AF_INET, SOCK_DGRAM)
                s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                s.bind((self.me, self.port))
                data, addr = s.recvfrom(1024)
                if data[:10] == self.req:
                    message = data[10:]
                    if addr[0] in self.peers:
                        other_key = self.peers[addr[0]]
                        enc = decrypt(self.key, message)
                        print(f"{enc.decode('utf-8')} from {addr[0]}")
                s.close()
    
    
    def start(self):
        interactions = [
            self.broadcast,
            self.record,
            self.request,
            self.receive
        ]
        for action in interactions:
            action_thread = threading.Thread(target=action)
            action_thread.start()