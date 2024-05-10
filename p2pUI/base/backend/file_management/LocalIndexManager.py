import os
import hashlib
import json
import logging


class LocalIndexManager:
    logging.basicConfig(filename="std.log", filemode="a", level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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
            if os.path.isfile(file_path):
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
