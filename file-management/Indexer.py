import os
import hashlib
import json
import time
from Overwatcher import DirectoryMonitor

class LocalFileIndexer:
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
        
        file_hash = None
        for file_hash, meta_data in self.file_hashes.items():
            if meta_data['name'] == filename:
                file_hash = file_hash
                break
        
        if file_hash and file_hash in self.file_hashes:
            del self.file_hashes[file_hash]
            self.save_index_to_json()

    def get_index(self):
        return self.file_hashes

class PeerIndexManager:
    def __init__(self, index_file='peer_index.json'):
        self.index_file = index_file #Locally stored index file of peers combined
        self.peer_file_index = self.load_index_from_file() #Loaded dictionary of file hashes and their metadata

    def load_index_from_file(self):
        """Load the peer file index from a JSON file."""
        if os.path.exists(self.index_file):
            with open(self.index_file, 'r') as file:
                return json.load(file)
        else:   
            return {}

    def save_index_to_file(self):
        """Save the peer file index to a JSON file."""
        with open(self.index_file, 'w') as file:
            json.dump(self.peer_file_index, file, indent=4)

def update_from_received_index(self, received_index_json, peer_address):
    """Update the local index from a received JSON index from a peer."""
    received_index = json.loads(received_index_json)
    
    for file_hash, file_attrs in received_index.items():
        file_metadata = {
            "name": file_attrs["name"],
            "size": file_attrs["size"],
        }
        if file_hash not in self.peer_file_index: #if hash is not in the peer file, we create a new entry with hash as key 
            self.peer_file_index[file_hash] = {
                "metadata": file_metadata,
                "peers": {}
            }
        else:
            # If the hash is present we just update a peer dictionary with new pair of peer address and last update time
            self.peer_file_index[file_hash]["peers"][peer_address] = {
                "last_update": time.time(),
            }
    self.save_index_to_file()


    def get_file_peers(self, file_hash):
        """Get the peers that have the file with the given hash."""
        return self.peer_file_index[file_hash]["peers"] #return the dictionary of peers with last update time

    def list_available_files(self):
        return [self.peer_file_index[file_hash]["metadata"]["name"] for file_hash in self.peer_file_index]

if __name__ == "__main__":
    shared_folder_mac = r'/Users/finik/Desktop/FilesToTransfer'
    file_indexer = LocalFileIndexer(shared_folder_mac)
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