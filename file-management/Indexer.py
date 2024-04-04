import os
import hashlib
import json
import time
from Overwatcher import DirectoryMonitor

class LocalIndexManger:
    def __init__(self, shared_folder, index_file_name='index.json'):
        self.shared_folder = shared_folder
        self.index_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), index_file_name)
        self.file_hashes = {}


    def generate_file_hash(self, file_path):
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as file: 
            while True:
                chunk = file.read(1024)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    
    
    def index_files(self):
        for filename in os.listdir(self.shared_folder):
            file_path = os.path.join(self.shared_folder, filename) 
            file_hash = self.generate_file_hash(file_path)
            self.file_hashes[file_hash] = {
                'name': filename,
                'path': file_path,
                'size': os.path.getsize(file_path)
            }
        self.save_index_to_json()


    def save_index_to_json(self):
        """Save the file index to a JSON file."""
        with open(self.index_file, 'w') as f:
            json.dump(self.file_hashes, f, indent=4)


    def add_index_to_json(self, file_path):
        if os.path.isfile(file_path): 
            file_hash = self.generate_file_hash(file_path)
            filename = os.path.basename(file_path)
            self.file_hashes[file_hash] = {
                'name': filename,
                'path': file_path,
                'size': os.path.getsize(file_path)
            }
            self.save_index_to_json()

    def delete_index_from_json(self, file_path):
        filename = os.path.basename(file_path)
        
        file_hash_to_delete = None
        for file_hash, meta_data in self.file_hashes.items():
            if meta_data['name'] == filename:
                file_hash_to_delete = file_hash
                break
        
        if file_hash and file_hash in self.file_hashes:
            del self.file_hashes[file_hash_to_delete]
            self.save_index_to_json()

    def get_index(self):
        return self.file_hashes

class PeerIndexManager:
    def __init__(self, peer_index_file_name='peer_index.json'):
        self.index_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), peer_index_file_name)
        self.file_indexes = {}

    def load_peer_index(self):
        try:
            with open(self.index_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
                return {}

    def save_peer_index(self):
        with open(self.index_file, 'w') as file:
            json.dump(self.file_indexes, file, indent=4)

    def add_file_from_peer_index(self, file_hash, file_metadata, peer_address):
        """Add a new file to the index or update existing file metadata."""
        if file_hash not in self.peer_file_index:
            self.peer_file_index[file_hash] = {
                "metadata": file_metadata,
                "peers": {}
            }
        self.peer_file_index[file_hash]["peers"][peer_address] = {
            "last_update": time.time()
        }
        self.save_peer_index()

    def remove_file_from_peer_index(self, file_hash, peer_address):
        if file_hash in self.peer_file_index:
            if peer_address in self.peer_file_index[file_hash]["peers"]:
                del self.peer_file_index[file_hash]["peers"][peer_address]
                if not self.peer_file_index[file_hash]["peers"]:
                    del self.peer_file_index[file_hash]
                self.save_peer_index()
                
    def get_file_peers(self, file_hash):
        """Get the peers that have the file with the given hash."""
        return self.peer_file_index[file_hash]["peers"] #return the dictionary of peers with last update time

    def list_available_files(self):
        return [self.peer_file_index[file_hash]["metadata"]["name"] for file_hash in self.peer_file_index]

if __name__ == "__main__":
    shared_folder_mac = r'/Users/finik/Desktop/FilesToTransfer'
    file_indexer = LocalIndexManger(shared_folder_mac)
    peer_file_indexer = PeerIndexManager()
    peer_file_indexer.save_peer_index()
    file_indexer.index_files()
    print(f"Indexing complete. Data saved in {file_indexer.index_files}.")
    time.sleep(5)
    monitor = DirectoryMonitor(shared_folder_mac, file_indexer)
    monitor.start()

    try:
        while True:
            pass 
    except KeyboardInterrupt:
        monitor.stop()