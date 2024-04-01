import os
import hashlib

class FileIndexer:
    def __init__(self, shared_folder):
        self.shared_folder = shared_folder
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


shared_folder = r'C:\FileTransfers'  
file_indexer = FileIndexer(shared_folder)
file_indexer.index_files()

for file_hash, metadata in file_indexer.file_hashes.items():
    print(f"{file_hash}: {metadata}")