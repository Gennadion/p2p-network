import json
import threading
import time
import logging
import socket

class Peer:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def __init__(self, addr, mask, port=9613, file_manager=None, messager=None):
        self.logger = logging.getLogger(__name__)
        logging.info(f"Initializing Peer at {addr} on port {port}")
        self.messager = messager
        self.files = []
        self.hello = b'Imma here!'
        self.peers = {}
        self.file_batch_size = 64
        self.file_manager = file_manager
        self.me = addr
        self.stop_event = threading.Event()

    def listen_for_broadcasts(self):
        while not self.stop_event.is_set():
            try:
                data, addr = self.messager.record()
                if addr[0] == self.me:
                    continue  

                if data[:10] == self.hello and addr[0] != self.me and addr[0] not in self.peers:
                    new_peer_address = addr[0]
                    self.peers[new_peer_address] = {"last_online": time.time()}
                    logging.info(f"Discovered new peer at {new_peer_address}")
                    self.file_manager.share_index_file_with_new_peer(new_peer_address)
                elif data[:10] == self.hello and addr[0] in self.peers:
                    self.peers[addr[0]]["last_online"] = time.time()
                else:
                    logging
                    self.file_manager.handle_received_message(json.loads(data.decode("utf-8")), addr)
            except socket.timeout:
                continue
            except Exception as e:
                logging.error(f"Error during peer discovery: {e}")
            finally: 
                if self.stop_event.is_set():
                    break

    def listen_for_direct_messages(self):
        while not self.stop_event.is_set():
            try:
                data, addr = self.messager.receive()
                if data:
                    self.file_manager.handle_received_message(json.loads(data.decode("utf-8")), addr)
            except socket.timeout: 
                continue
            except Exception as e:
                logging.error(f"Error receiving direct message: {e}")
            finally:
                if self.stop_event.is_set():
                    break

    def discover_peers(self):
        logging.info("Starting peer discovery...")
        
        last_broadcast_time = time.time() 
        time.sleep(15)  

        while not self.stop_event.is_set():
            current_time = time.time()
            time_since_last_broadcast = current_time - last_broadcast_time

            if time_since_last_broadcast >= 15:
                try:
                    logging.info("Broadcasting hello message...")
                    self.messager.broadcast(self.hello)
                    last_broadcast_time = time.time()
                except Exception as e:
                    logging.error(f"Error broadcasting hello message: {e}")


    def send_updates(self, message_to_send):
        logging.info("Sending updates to peers...")
        for peer in self.peers.keys():
            try:
                self.messager.send(peer, message_to_send)
            except Exception as e:
                logging.error(f"Error sending updates to {peer}: {e}")

    def send_index(self, peer_address, message_to_send):
        logging.info(f"Sending index to {peer_address}")
        try:
            self.messager.send(peer_address, message_to_send)
        except Exception as e:
            logging.error(f"Error sending index to {peer_address}: {e}")

    def kill_timeouts(self):
        logging.info("Monitoring for peer timeouts...")
        while not self.stop_event.is_set():
            for peer in list(self.peers):
                if time.time() - self.peers[peer]["last_online"] > 15:
                    logging.info(f"Peer {peer} timed out")
                    self.file_manager.handle_disconnected_peer(peer)
                    del self.peers[peer]
            time.sleep(20)

    def start(self):
        logging.info("Starting Peer operations")
        self.threads = []
        interactions = [self.listen_for_broadcasts, self.discover_peers, self.kill_timeouts, self.listen_for_direct_messages]
        self.stop_event.clear()
        for action in interactions:
            thread = threading.Thread(target=action, daemon=True)
            thread.start()
            self.threads.append(thread)
    def stop(self):
        logging.info("Stopping Peer operations")
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=5)  
