import threading
from ..backend.networks.peer import Peer
from .file_management.FileManager import FileManager
from .file_management.LocalIndexManager import *
from .file_management.PeerIndexer import *
from .file_management.ChunkProcessor import *


def generate_response(files, origin, metadata_keys, main_key, inner_metadata_keys=None):
    response = {origin: []}
    for hsh, metadata in files.items():
        new_elem = {
            main_key: hsh,
            "origin": origin
        }
        for key in metadata_keys:
            new_elem[key] = metadata[key]
            if inner_metadata_keys and key == "metadata":
                for inner_key in inner_metadata_keys:
                    new_elem[inner_key] = metadata[key][inner_key]
        response[origin].append(new_elem)
    return response


class Node:
    logging.basicConfig(filename="std.log", filemode="a", level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def __init__(self,
                 addr,
                 mask,
                 shared_folder,
                 index_file_name='index.json',
                 peer_index_file_name='peer_index.json',
                 port=9613,
                 me=None
                 ):
        self.logger = logging.getLogger(__name__)
        local_indexer = LocalIndexManager(shared_folder, index_file_name)
        local_indexer.index_files()

        peer_indexer = PeerIndexManager(peer_index_file_name)
        peer_indexer.load_peer_index()

        self.peer = Peer(self, addr, mask, peer_indexer, port, me)

        self.file_manager = FileManager(self, shared_folder, local_indexer)

        self.chunk_processor = None

        jobs = [
            self.peer.start,
            self.file_manager.directory_monitor.start
        ]

        self.threads = map(lambda job: threading.Thread(target=job, daemon=True), jobs)

        self.event_dictionary = {
            "new_peer": self.handle_new_peer,
            "send_file_update": self.send_file_update,
            "got_chunk": self.handle_new_chunk,
            "request_file": self.request_file,
            "save_file": self.save_file,
            "request_chunk": self.request_chunk,
            "handle_file_request": self.handle_file_request
        }

    def run(self):
        for thread in self.threads:
            thread.start()

    def stop(self):
        logging.info("Shutting down P2P client...")
        self.file_manager.directory_monitor.stop()
        self.file_manager.clear_indices()
        self.peer.stop()
        for thread in self.threads:
            thread.join(timeout=2)

    def run_forever(self):
        self.run()
        try:
            while True:
                pass
        except KeyboardInterrupt:
            self.stop()

    def handle_new_peer(self, event):
        addr = event["addr"]
        self.logger.info(f"Handling new peer {addr}")
        my_file_index = self.file_manager.get_full_index()
        my_file_index_bytes = json.dumps(my_file_index).encode('utf-8')
        self.peer.send_index(addr, my_file_index_bytes)

    def send_file_update(self, event):
        self.logger.info("sent file update")
        update_bytes = json.dumps(event["update"]).encode('utf-8')
        self.peer.send_updates(None, update_bytes)

    def handle_file_request(self, event):
        try:
            data = event["data"]
            peer_address = event["addr"]
            file_hash = data["file_hash"]
            bit_offset = data["bit_offset"]
            chunk_size = data["chunk_size"]
            file_path = self.file_manager.get_file_path(file_hash)
            with open(file_path, 'rb') as f:
                f.seek(bit_offset)
                chunk = f.read(chunk_size)
            chunk_info = data
            self.peer.send_file_chunk(peer_address, json.dumps(chunk_info).encode('utf-8'), chunk)
            self.logger.info(
                f"Sent file chunk from bit: {bit_offset} to {bit_offset + chunk_size} to address: {peer_address}")
        except Exception as e:
            self.logger.error(f"Error handling file request: {e}")

    def handle_new_chunk(self, event):
        self.logger.info("received new chunk")
        data = event["chunk_data"]
        chunk_info = json.loads(data.decode('utf-8'))
        chunk_info["chunk_data"] = event["chunk"]
        self.chunk_processor.handle_chunk(chunk_info)

    def request_file(self, event):
        if self.chunk_processor is None:
            self.logger.info(f"Requesting file: {event['file_hash']}")
            file_hash = event["file_hash"]
            selected_file = self.peer.get_peer_file(file_hash)
            self.chunk_processor = ChunkProcessor(self, file_hash, selected_file)
            if selected_file:
                logging.info(
                    f"Selected file: {selected_file['name']} ({selected_file['size']} bytes)")
                logging.info(f"Starting download for file hash {file_hash}.")
                result = self.chunk_processor.download_and_verify_file()
                if result:
                    self.logger.info(f"Saved and verified file {file_hash}")
                    self.chunk_processor = None
                    return
                self.logger.error(f"Error downloading file with hash {file_hash}.")
                self.chunk_processor = None
                return
            self.logger.error(f"File with hash {file_hash} not found in peer index.")
            self.chunk_processor = None
        else:
            self.logger.info(f"Requested {event} while downloading other file")

    def save_file(self, event):
        self.file_manager.save_file(event["name"], event["data"])

    def get_file_peers(self, file_hash):
        result = self.peer.get_file_peers(file_hash)
        return result

    def request_chunk(self, event):
        self.logger.info(f"Requesting chunk for file: {event['file_hash']}")
        chosen_peer = event["peer_address"]
        del event["action"]
        del event["peer_address"]
        self.peer.send_request(chosen_peer, json.dumps(event).encode('utf-8'))
        return True

    def handle_event(self, event):
        if "action" not in event:
            self.logger.error(f"No action event: {event}")
            return
        self.logger.info(f"handling event {event['action']}")
        if event["action"] in self.event_dictionary:
            self.event_dictionary[event["action"]](event)
            return
        self.logger.error(f"Unrecognized event: {event['action']}")

    def get_local_files(self):
        files = self.file_manager.get_full_index()
        response = generate_response(files, "local_files", ["name", "size"], "hash")
        return response

    def get_downloading(self):
        response = {"requested_file": []}
        if self.chunk_processor is None:
            return response
        response["requested_file"].append({
            "name": self.chunk_processor.name,
            "size": self.chunk_processor.size,
            "hash": self.chunk_processor.file_hash,
            "origin": "requested_file"
        })

    def get_net_files(self):
        files = self.peer.peer_indexer.get_peer_index()
        response = generate_response(files, "net_files", ["metadata", "peers"], "hash", ["name", "size"])
        return response

    def get_active_peers(self):
        response = generate_response(self.peer.peers, "active_peers", ["key", "last_online"], "address")
        return response
