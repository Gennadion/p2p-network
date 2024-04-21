import os
import hashlib
import json
import time
import logging

class LocalIndexManager:
    logging.basicConfig(filename="std.log", filemode="a", level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    def __init__(self, shared_folder, index_file_name='index.json'):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing LocalIndexManager...")
        self.shared_folder = shared_folder
        self.index_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), index_file_name)
        self.file_hashes = {}

    def generate_file_hash(self, file_path):
        self.logger.debug(f"Generating file hash for {file_path}...")
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as file:
            while chunk := file.read(1024):
                hasher.update(chunk)
        return hasher.hexdigest()

    def index_files(self):
        self.logger.info("Indexing files...")
        for filename in os.listdir(self.shared_folder):
            file_path = os.path.join(self.shared_folder, filename)
            file_hash = self.generate_file_hash(file_path)
            self.file_hashes[file_hash] = {'name': filename, 'path': file_path, 'size': os.path.getsize(file_path)}
        self.save_index_to_json()
        self.logger.info("Indexing complete.")

    def save_index_to_json(self):
        self.logger.info("Saving index to JSON...")
        with open(self.index_file, 'w') as f:
            json.dump(self.file_hashes, f, indent=4)
        self.logger.info("Index saved.")

    def add_index_to_json(self, file_path):
        self.logger.info(f"Adding {file_path} to index...")
        if os.path.isfile(file_path):
            file_hash = self.generate_file_hash(file_path)
            filename = os.path.basename(file_path)
            self.file_hashes[file_hash] = {'name': filename, 'path': file_path, 'size': os.path.getsize(file_path)}
            self.save_index_to_json()
            self.logger.info(f"{file_path} added to index.")
            return file_hash, self.file_hashes[file_hash]

    def delete_index_from_json(self, file_path):
        self.logger.info(f"Deleting {file_path} from index...")
        filename = os.path.basename(file_path)
        file_hash_to_delete = None
        for file_hash, meta_data in self.file_hashes.items():
            if meta_data['name'] == filename:
                file_hash_to_delete = file_hash
                break
        if file_hash_to_delete and file_hash_to_delete in self.file_hashes:
            del self.file_hashes[file_hash_to_delete]
            self.save_index_to_json()
            self.logger.info(f"{file_path} deleted from index.")
            return file_hash_to_delete

    def get_index(self):
        return self.file_hashes
    
    def clear_local_index(self):
        self.logger.info("Clearing local index...")
        self.file_hashes = {}
        self.save_index_to_json()
        self.logger.info("Local index cleared.")

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