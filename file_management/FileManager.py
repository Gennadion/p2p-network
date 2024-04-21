import json
import logging
import os 

class FileManager:
    logging.basicConfig(filename="std.log", filemode="a", level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    def __init__(self, shared_folder, index_file_name='index.json', peer_index_file_name='peer_index.json', peer_object=None, local_indexer=None, peer_indexer=None):
        self.logger = logging.getLogger(__name__)
        logging.info(f"Initializing FileManager for {shared_folder}")
        self.shared_folder = shared_folder
        self.local_indexer = local_indexer
        self.peer_indexer = peer_indexer
        self.peer = peer_object
    def format_message(self, action, data):
        """Format a message with a specified action and data."""
        message = {
            "action": action,
            "data": data
        }
        return json.dumps(message)

    def create_update_message(self, action, file_hash, metadata=None):
        """Create a message to update peers about a file index change."""
        message = {
            "action": action,
            "file_hash": file_hash
        }
        if metadata:
            message["metadata"] = metadata
        return message

    def share_index_file_with_new_peer(self, peer_address):
        """Share the local index file with a new peer in the P2P network, excluding local path information."""
        try:
            local_index_file = self.local_indexer.get_index()
            index_to_send = {}
            for file_hash, metadata in local_index_file.items():
                filtered_metadata = {"name": metadata["name"], "size": metadata["size"]}
                index_to_send[file_hash] = filtered_metadata
            
            message = self.format_message("index_all", index_to_send)
            self.peer.send_index(peer_address, message.encode("utf-8"))
            logging.info(f"Index shared with new peer: {peer_address}")
        except Exception as e:
            logging.error(f"Error sharing index with new peer {peer_address}: {e}")

    def handle_index_file_from_peer(self, peer_address, index_file):
        """Handle the index file received from a peer."""
        try:
            self.peer_indexer.update_from_received_index(index_file, peer_address)
            self.refresh()
            logging.info(f"Received and processed index file from peer: {peer_address}")
        except Exception as e:
            logging.error(f"Error processing index file from {peer_address}: {e}")

    def share_file_index(self, file_path):
        """Share a newly added file index with peers, only including the filename and size in the metadata."""
        try:
            file_hash, file_metadata = self.local_indexer.add_index_to_json(file_path)
            filtered_metadata = {
                "name": file_metadata["name"],
                "size": file_metadata["size"]
            }
            update_message = self.create_update_message("add", file_hash, filtered_metadata)
            self.peer.send_updates(self.format_message("index_add", update_message).encode("utf-8"))
            logging.info(f"Shared file index for {file_path} with peers.")
        except Exception as e:
            logging.error(f"Error sharing file index for {file_path}: {e}")

    def unshare_file_index(self, file_path):
        """Unshare a file index with peers."""
        try:
            file_hash = self.local_indexer.delete_index_from_json(file_path)
            update_message = self.create_update_message("delete", file_hash)
            self.peer.send_updates(self.format_message("index_remove", update_message).encode("utf-8"))
            logging.info(f"Unshared file index for {file_path}")
        except Exception as e:
            logging.error(f"Error unsharing file index for {file_path}: {e}")

    def process_peer_update(self, update_message, addr):
        """Process a file update message from a peer."""
        try:
            action = update_message['action']
            file_hash = update_message['file_hash']
            peer_address = addr
            
            if action == 'add':
                self.peer_indexer.add_file_index(file_hash, update_message['metadata'], peer_address)
                self.refresh()
            elif action == 'delete':
                self.peer_indexer.remove_file_index(file_hash, peer_address)
                self.refresh()
            logging.info(f"Processed peer update: {action} for file {file_hash}")
        except Exception as e:
            logging.error(f"Error processing peer update: {e}")

    def handle_disconnected_peer(self, peer_address):
        """Handle disconnected peers by removing all records associated with this peer address."""
        try:
            self.peer_indexer.remove_disconnected_peer(peer_address)
            logging.info(f"Handled disconnected peer: {peer_address}")
        except Exception as e:
            logging.error(f"Error handling disconnected peer {peer_address}: {e}")

    def handle_received_message(self, received_message, addr):
        """Handle a received message."""
        try:
            action = received_message["action"]
            data = received_message["data"]
            logging.info(f"Received message: {action} for data {data} from {addr}")
            if action in ["index_add", "index_remove"]:
                self.process_peer_update(data, addr[0])
            elif action == "index_all":
                self.handle_index_file_from_peer(addr[0], data)
            logging.info(f"Handled received message from {addr}")
        except Exception as e:
            logging.error(f"Error handling received message from {addr}: {e}")

    def display_terminal(self):
        print("\n==============================================================================================================================================================\n")
        for file_hash, file_info in self.peer_indexer.get_peer_index().items():
            print(f"\n{file_info['metadata']['name']} ({file_info['metadata']['size']} bytes)\nFile hash - {file_hash}")
            print("Available from peers:")
            for i, peer in enumerate(list(file_info['peers'].keys()), start=1):
                print(f"    {i}. {peer}")
        print("\nType 'refresh' to update this list, or 'exit' to quit.")


    def refresh(self):
        print("Update is detected, refreshing...")
        self.peer_indexer.load_peer_index()
        self.display_terminal()

    def terminal_command_loop(file_manager):
        while True:
            command = input("Enter command (refresh, ...): ").strip().lower()
            if command == "refresh":
                file_manager.refresh()
            elif command == "exit":
                break
            else:
                print("Unknown command.")    