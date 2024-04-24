import threading
from networks.peer import Peer
from file_management.FileManager import FileManager
from file_management.LocalIndexManager import *
from file_management.PeerIndexer import *
from file_management.ChunkProcessor import *


class Node:
    logging.basicConfig(filename="std.log", filemode="a", level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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
            "request_chunk": self.request_chunk
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
        update_bytes = json.dumps(event["update"])
        self.peer.send_updates(None, update_bytes)

    def handle_file_request(self, event):
        try:
            file_hash = event["file_hash"]
            bit_offset = event["bit_offset"]
            chunk_size = event["chunk_size"]
            peer_address = event["addr"]
            file_path = self.file_manager.get_file_path(file_hash)
            with open(file_path, 'rb') as f:
                f.seek(bit_offset)
                chunk = f.read(chunk_size)
            chunk_info = event
            chunk_info["data"] = chunk
            del event["action"]
            del event["addr"]
            self.peer.send_file_chunk(peer_address, json.dumps(chunk_info))
            logging.info(
                f"Sent file chunk from bit: {bit_offset} to {bit_offset + chunk_size} to address: {peer_address}")
        except Exception as e:
            logging.error(f"Error handling file request: {e}")

    def handle_new_chunk(self, event):
        data = event["chunk_data"]
        chunk_info = json.loads(data)
        self.chunk_processor.handle_chunk(chunk_info)

    def request_file(self, event):
        file_hash = event["hash"]
        selected_file = self.file_manager.get_file_data(file_hash)
        self.chunk_processor = ChunkProcessor(self, file_hash, selected_file)
        if selected_file:
            logging.info(
                f"Selected file: {selected_file['metadata']['name']} ({selected_file['metadata']['size']} bytes)")
            logging.info(f"Starting download for file hash {file_hash}.")
            result = self.chunk_processor.download_and_verify_file()
            if result:
                self.chunk_processor.clear_temp_storage(file_hash)
                return
            logging.error(f"Error downloading file with hash {file_hash}.")
            return
        logging.error(f"File with hash {file_hash} not found in peer index.")

    def save_file(self, event):
        self.file_manager.save_file(event["name"], event["data"])

    def peer_file_lookup(self, file_hash):
        result = self.peer.get_file_peers(file_hash)
        return result

    def request_chunk(self, event):
        chosen_peer = event["peer_address"]
        del event["action"]
        del event["peer_address"]
        self.peer.send_request(chosen_peer, event)
        return True

    def handle_event(self, event):
        if event["action"] in self.event_dictionary:
            self.event_dictionary[event["action"]](event)
            return
        logging.error(f"Unrecognized event: {event['action']}")
