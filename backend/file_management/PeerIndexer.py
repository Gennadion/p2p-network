import json
import logging
import os
import time


class PeerIndexManager:
    def __init__(self, peer_index_file_name='peer_index.json'):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing PeerIndexManager...")
        self.index_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), peer_index_file_name)
        self.peer_file_index = self.load_peer_index()
        self.file_indexes = {}

    def load_peer_index(self):
        self.logger.info("Loading peer index...")
        try:
            with open(self.index_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning("Peer index file not found, starting fresh.")
            return {}

    def get_peer_index(self):
        index_file = self.load_peer_index()
        return index_file

    def save_peer_index(self):
        self.logger.info("Saving peer index...")
        with open(self.index_file, 'w') as f:
            json.dump(self.file_indexes, f, indent=4)
        self.logger.info("Peer index saved.")

    def add_file_index(self, file_hash, file_metadata, peer_address):
        self.logger.debug(f"Adding file index for hash {file_hash} from peer {peer_address}...")
        if file_hash not in self.peer_file_index:
            self.peer_file_index[file_hash] = {"metadata": file_metadata, "peers": {}}
        self.peer_file_index[file_hash]["peers"][peer_address] = {"last_update": time.time()}
        self.file_indexes = self.peer_file_index
        self.save_peer_index()
        self.logger.info(f"File index for {file_hash} added from peer {peer_address}.")

    def remove_file_index(self, file_hash, peer_address):
        self.logger.debug(f"Removing file index for hash {file_hash} from peer {peer_address}...")
        if file_hash in self.peer_file_index and peer_address in self.peer_file_index[file_hash]["peers"]:
            del self.peer_file_index[file_hash]["peers"][peer_address]
            if not self.peer_file_index[file_hash]["peers"]:
                del self.peer_file_index[file_hash]
            self.save_peer_index()
            self.logger.info(f"File index for {file_hash} removed for peer {peer_address}.")
        else:
            self.logger.warning(f"File with hash {file_hash} or peer {peer_address} not found in peer index.")

    def get_file_peers(self, file_hash):
        self.logger.debug(f"Getting peers for file hash {file_hash}...")
        if file_hash in self.peer_file_index:
            return self.peer_file_index[file_hash]["peers"]
        else:
            self.logger.warning(f"File with hash {file_hash} not found in peer index.")
            return {}

    def list_available_files(self):
        self.logger.info("Listing all available files from peer index...")
        return [self.peer_file_index[file_hash]["metadata"]["name"] for file_hash in self.peer_file_index]

    def update_from_received_index(self, index_file, peer_address):
        self.logger.info(f"Updating peer index from received index file from {peer_address}...")
        for file_hash, metadata in index_file.items():
            self.add_file_index(file_hash, metadata, peer_address)
            self.logger.info(f"Peer index updated from {peer_address}.")

    def remove_disconnected_peer(self, peer_address):
        self.logger.info(f"Removing disconnected peer {peer_address} from peer index...")
        hashes_to_remove = []
        for file_hash in list(self.peer_file_index.keys()):
            if peer_address in self.peer_file_index[file_hash]["peers"]:
                del self.peer_file_index[file_hash]["peers"][peer_address]
                if not self.peer_file_index[file_hash]["peers"]:
                    hashes_to_remove.append(file_hash)

        for hash in hashes_to_remove:
            del self.peer_file_index[hash]

        self.save_peer_index()
        self.logger.info(f"Disconnected peer {peer_address} removed successfully from peer index.")

    def clear_peer_index(self):
        self.logger.info("Clearing peer index...")
        self.index_file = {}
        self.save_peer_index()
        self.logger.info("Peer index cleared.")
