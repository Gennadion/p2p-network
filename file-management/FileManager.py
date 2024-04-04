from Indexer import LocalFileIndexer
from Indexer import PeerIndexManager
from networks import interaction as network_interaction

class FileManager:
    def __init__(self, shared_folder, index_file_name='index.json', peer_index_file_name='peer_index.json'):
        self.shared_folder = shared_folder
        self.local_indexer = LocalFileIndexer(shared_folder, index_file_name)
        self.peer_indexer = PeerIndexManager(peer_index_file_name)
        self.messenger = network_interaction.Messager(addr="192.168.230.6", mask="255.255.255.0")
    
    def create_update_message(self, action, file_hash, file_metadata=None):
        """Create an update message for broadcasting to peers."""
        update_message = {
            "action": action,
            "file_hash": file_hash
        }
        if file_metadata: #if file metadata is provided, add it to the update message
            update_message["metadata"] = file_metadata
        return update_message
    
    def share_file(self, file_path):
        """Share a newly added file with peers."""
        file_hash = self.local_indexer.add_index_to_json(file_path)
        file_metadata = self.local_indexer.get_index()[file_hash]
        update_message = self.create_update_message(action="add", h=file_hash, meta_data=file_metadata)
        self.messenger.broadcast_update(update_message) #method to send out the update message to all peers
 
    def unshare_file(self, file_path):
        """Unshare a file with peers."""
        file_hash = self.local_indexer.delete_index_from_json(file_path)
        update_message = self.create_update_message(action="delete", h=file_hash)
        self.messenger.broadcast_update(update_message)

    def process_peer_update(self, update_message):

        """Process a file update message from a peer."""
        action = update_message['action']
        file_hash = update_message['file_hash']
        peer_address = update_message['peer_address']  # Assuming this is included in the message
        
        if action == 'add':
            file_metadata = update_message['metadata']
            self.peer_indexer.add_file_index(file_hash, file_metadata, peer_address)
        elif action == 'remove':
            self.peer_indexer.remove_file_index(file_hash, peer_address)