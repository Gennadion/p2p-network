from socket import *

from encryption import encrypt, create_key, decrypt


class Messager:
    def __init__(self, addr, mask, port=9613, me=None):
        self.me = me
        self.key, self.pkey = create_key()
        self.port = port
        self.bcast = '.'.join(
            list(map(str, [int(a) | (255 ^ int(m)) for a, m in zip(addr.split('.'), mask.split('.'))])))

    def broadcast(self, message):
        s = socket(AF_INET, SOCK_DGRAM)
        s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        s.sendto(message, (self.bcast, self.port))
        s.close()

    def send(self, key, addr, message):
        s = socket(AF_INET, SOCK_STREAM)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        enc = encrypt(key, message)
        s.connect((addr, self.port))
        for i in range(len(enc) // 1024):
            s.send(enc[i:i + 1024])
        s.close()

    def record(self):
        s = socket(AF_INET, SOCK_DGRAM)
        s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind((self.bcast, self.port))
        data, addr = s.recvfrom(32768)
        s.close()
        return data, addr

    def receive(self):
        if self.me:
            s = socket(AF_INET, SOCK_STREAM)
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.bind((self.me, self.port))
            s.listen()
            conn, addr = s.accept()
            data = []
            batch = conn.recvfrom(1024)
            while batch:
                data += batch
                batch = conn.recvfrom(1024)
            message = decrypt(self.key, data)
            s.close()
            return message, addr
