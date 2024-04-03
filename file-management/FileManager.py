from Indexer import LocalFileIndexer
from Indexer import PeerIndexManager

class FileManager:
    def __init__(self, shared_folder, index_file_name='index.json', peer_index_file_name='peer_index.json'):
        self.shared_folder = shared_folder
        self.local_indexer = LocalFileIndexer(shared_folder, index_file_name)
        self.peer_indexer = PeerIndexManager(peer_index_file_name)
        
    def get_index_from_peer(self):
        """Gets index of shared files from discovered peers by network module."""
    def send_index_with_peers(self): 
        """Gets index of shared files from file indexer module and shares it with discovered peers by network module."""
