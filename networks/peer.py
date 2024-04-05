import json
import threading
import time
from messager import Messager


class Peer:
    def __init__(self, addr, mask, port=9613, me=None):
        self.messager = Messager(addr, mask, port, me)
        self.files = []
        self.hello = b'Imma here!'
        self.req = b'Gimme dat!'
        self.file_alert = b'I have dis'
        self.resp = b'Sendin dat'
        self.peers = {}

    def add_file(self, path, hsh, size, name):
        self.files.append({
            "path": path,
            "hsh": hsh,
            "size": size,
            "name": name
        })

    def alert(self):
        while True:
            self.messager.broadcast(self.hello + self.messager.pkey)
            time.sleep(1)

    def discover_peers(self):
        while True:
            data, addr = self.messager.record()
            if data[:10] == self.hello and addr[0] != self.messager.me:
                if data[10:] == self.messager.pkey:
                    self.messager.me = addr[0]
                    print(f"I am existing as {self.messager.me}")
                    continue
                if addr[0] not in self.peers:
                    self.peers[addr[0]] = {
                        "key": data[10:],
                        "files": []
                    }
            if data[:10] == self.file_alert and addr[0] in self.peers:
                self.peers[addr[0]]["files"] = json.loads(data[10:].decode("utf-8"))
                continue

    def alert_files(self):
        while True:
            self.messager.broadcast(self.file_alert + json.dumps(self.files).encode("utf-8"))
            time.sleep(1)

    def get_request(self):
        while True:
            data, addr = self.messager.receive()
            if data[:10] == self.req:
                if addr[0] in self.peers:
                    # this part should be connected somehow to file transferring
                    print(f"request {data[10:].decode('utf-8')} from {addr[0]}")
            if data[:10] == self.resp:
                if addr[0] in self.peers:
                    # this part should be connected somehow to file transferring
                    print(f"response {data[10:].decode('utf-8')} from {addr[0]}")

    def send_request(self, peer_addr, request):
        if peer_addr in self.peers:
            self.messager.request(self.peers[peer_addr]["key"], peer_addr, self.req + request)

    def send_data(self, peer_addr, response):
        if peer_addr in self.peers:
            self.messager.request(self.peers[peer_addr]["key"], peer_addr, self.resp + response)

    def start(self):
        interactions = [
            self.alert,
            self.discover_peers,
            self.alert_files,
            self.get_request
        ]
        for action in interactions:
            action_thread = threading.Thread(target=action)
            action_thread.start()
