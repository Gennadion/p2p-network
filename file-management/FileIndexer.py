import os
import hashlib

class FileIndexer:
    def __init__(self, shared_folder):
        self.shared_folder = shared_folder
        self.file_hashes = {}

    def generate_file_hash(self, file_path):  # Take a file_path as argument
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as file:  # Open the file to read in binary mode
            while True:
                chunk = file.read(1024)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

# Usage
file_path = r'C:\FileTransfers\ethernet-wireshark-trace1.pcapng' 
file_indexer = FileIndexer(file_path)  
print(file_indexer.generate_file_hash(file_path))
