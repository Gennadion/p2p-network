import os
import hashlib
import json
import time
from file_management.Overwatcher import DirectoryMonitor

class FileIndexer:
    def __init__(self, shared_folder, index_file_name='index.json'):
        self.shared_folder = shared_folder
        # Set the path to the index file in the same directory as the script
        self.index_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), index_file_name)
        self.file_hashes = {}


    def generate_file_hash(self, file_path):
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as file:  # Open the file to read in binary mode
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


    def delete_index(self):
        if os.path.exists(self.index_file):
            os.remove(self.index_file)
            print(f"Cleaned up {self.index_file}.")


if __name__ == "__main__":
    shared_folder = r'C:\FileTransfers'  
    shared_folder_mac = r'/Users/finik/Desktop/FilesToTransfer'
    shared_folder_win = r'C:\Users\Genn\Desktop\shared_files'
    file_indexer = FileIndexer(shared_folder_win)
    file_indexer.index_files()
    print(f"Indexing complete. Data saved in {file_indexer.index_files}.")
    time.sleep(5)
    monitor = DirectoryMonitor(shared_folder_win, file_indexer)
    monitor.start()

    try:
        while True:
            # Keep the program running to monitor directory changes
            pass 
    except KeyboardInterrupt:
        monitor.stop()