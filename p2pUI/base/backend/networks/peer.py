import json
import logging
import threading
import time
import struct
from .messager import Messager


class Peer:
    logging.basicConfig(filename="std.log", filemode="a", level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def __init__(self, node, addr, mask, peer_indexer, port=9613, me=None):
        self.node = node
        self.messager = Messager(addr, mask, port, me)
        self.files = []
        self.hello = b'Imma here!'
        self.req = b'Gimme dat!'
        self.file_alert = b'I have dis'
        self.file_update = b'Update dis'
        self.resp = b'Sendin dat'
        self.peers = {}
        self.stop_event = threading.Event()
        self.threads = []
        self.peer_indexer = peer_indexer
        self.message_matcher = {
            self.file_alert: self.receive_index,
            self.file_update: self.receive_file_update,
            self.resp: self.receive_file_chunk,
            self.req: self.receive_file_request
        }
        self.logger = logging.getLogger(__name__)

    def alert(self):
        while not self.stop_event.is_set():
            self.messager.broadcast(self.hello + self.messager.pkey)
            time.sleep(1)

    def discover_peers(self):
        while not self.stop_event.is_set():
            data, addr = self.messager.record()
            self.logger.info(f"Broadcast message from: {addr}")
            if data[:10] == self.hello and addr[0] != self.messager.me:
                if data[10:] == self.messager.pkey:
                    self.messager.me = addr[0]
                    self.logger.info(f"I am existing as {self.messager.me}")
                    continue
                if addr[0] not in self.peers:
                    self.logger.info(f"New peer: {addr}")
                    self.peers[addr[0]] = {
                        "key": data[10:],
                        "last_online": time.time()
                    }
                    event = {
                        "action": "new_peer",
                        "addr": addr[0]
                    }
                    self.node.handle_event(event)
                self.peers[addr[0]]["last_online"] = time.time()
                self.logger.info(f"Time for peer {addr} updated")

    def send_index(self, peer_address, message):
        logging.info(f"Sending index to {peer_address}")
        message_to_send = self.file_alert + message
        try:
            self.messager.send(peer_address, message_to_send)
        except Exception as e:
            logging.error(f"Error sending index to {peer_address}: {e}")

    def send_updates(self, _, message):
        logging.info("Sending updates to peers...")
        message_to_send = self.file_update + message
        for peer in self.peers.keys():
            try:
                self.messager.send(peer, message_to_send)
            except Exception as e:
                logging.error(f"Error sending updates to {peer}: {e}")

    def send_file_chunk(self, peer_address, message, chunk):
        logging.info(f"Sending chunk to {peer_address}")
        length = struct.pack('!H', len(chunk))
        message_to_send = self.resp + length + chunk + message
        try:
            self.messager.send(peer_address, message_to_send)
        except Exception as e:
            logging.error(f"Error sending chunk to {peer_address}: {e}")

    def receive_index(self, peer_address, index_bytes):
        """Handle the index file received from a peer."""
        try:
            self.peer_indexer.update_from_received_index(json.loads(index_bytes.decode('utf-8')), peer_address)
            logging.info(f"Received and processed index file from peer: {peer_address}")
        except Exception as e:
            logging.error(f"Error processing index file from {peer_address}: {e}")

    def receive_file_update(self, peer_address, index_bytes):
        """Process a file update message from a peer."""
        try:
            update_message = json.loads(index_bytes.decode('utf-8'))
            action = update_message['action']
            file_hash = update_message['file_hash']
            if action == 'add':
                self.peer_indexer.add_file_index(file_hash, update_message['metadata'], peer_address)
            elif action == 'delete':
                self.peer_indexer.remove_file_index(file_hash, peer_address)
            logging.info(f"Processed peer update: {action} for file {file_hash}")
        except Exception as e:
            logging.error(f"Error processing peer update: {e}")

    def receive_file_request(self, peer_address, message_bytes):
        """Process a file request message from a peer."""
        try:
            update_message = json.loads(message_bytes.decode('utf-8'))
            event = {
                "action": "handle_file_request",
                "data": update_message,
                "addr": peer_address
            }
            self.node.handle_event(event)
            logging.info(f"Processed peer request from {peer_address}")
        except Exception as e:
            logging.error(f"Error processing peer request: {e}")

    def receive_file_chunk(self, peer_address, chunk_data):
        logging.info(f"Got chunk from {peer_address}")
        length = struct.unpack('!H', chunk_data[:2])[0]
        chunk = chunk_data[2:2 + length]
        event = {
            "action": "got_chunk",
            "chunk_data": chunk_data[2 + length:],
            "chunk": chunk
        }
        self.node.handle_event(event)

    def get_message(self):
        while not self.stop_event.is_set():
            if self.messager.me:
                data, addr = self.messager.receive()
                if data[:10] in self.message_matcher:
                    method = self.message_matcher[data[:10]]
                    method(addr[0], data[10:])
                    continue
                logging.error(f"Not recognized message from peer {addr[0]}: {data}")

    def send_request(self, peer_addr, request):
        if peer_addr in self.peers:
            self.messager.send(peer_addr, self.req + request)

    def handle_disconnected_peer(self, peer_address):
        """Handle disconnected peers by removing all records associated with this peer address."""
        try:
            self.peer_indexer.remove_disconnected_peer(peer_address)
            logging.info(f"Handled disconnected peer: {peer_address}")
            return True
        except Exception as e:
            logging.error(f"Error handling disconnected peer {peer_address}: {e}")

    def kill_timeouts(self):
        while not self.stop_event.is_set():
            dead_peers = []
            for peer in self.peers:
                if time.time() - self.peers[peer]["last_online"] > 60:
                    if self.handle_disconnected_peer(peer):
                        dead_peers.append(peer)
            for peer in dead_peers:
                del self.peers[peer]
            time.sleep(20)

    def get_file_peers(self, file_hash):
        peers_index = self.peer_indexer.get_peer_index()
        available_peers = peers_index[file_hash]["peers"]
        return available_peers
    
    def get_peer_file(self, file_hash):
        peers_index = self.peer_indexer.get_peer_index()
        metadata = peers_index[file_hash]["metadata"]
        return metadata

    def start(self):
        logging.info("Starting Peer operations")
        interactions = [
            self.alert,
            self.discover_peers,
            self.get_message,
            self.kill_timeouts
        ]
        self.stop_event.clear()
        for action in interactions:
            thread = threading.Thread(target=action, daemon=True)
            thread.start()
            self.threads.append(thread)

    def stop(self):
        logging.info("Stopping Peer operations")
        self.stop_event.set()
        self.messager.stop()
        for thread in self.threads:
            thread.join(timeout=2)
        self.peer_indexer.clear_peer_index()
