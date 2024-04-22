import json
import logging
import os 
import random 
import time
import hashlib 

class FileManager:
    logging.basicConfig(filename="std.log", filemode="a", level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    def __init__(self, shared_folder, index_file_name='index.json', peer_index_file_name='peer_index.json', peer_object=None, local_indexer=None, peer_indexer=None):
        self.logger = logging.getLogger(__name__)
        logging.info(f"Initializing FileManager for {shared_folder}")
        self.shared_folder = shared_folder
        self.local_indexer = local_indexer
        self.peer_indexer = peer_indexer
        self.peer = peer_object
        self.temp_file_storage = {}
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

    def display_terminal(self):
        print("\n==============================================================================================================================================================\n")
        for file_hash, file_info in self.peer_indexer.get_peer_index().items():
            print(f"\n{file_info['metadata']['name']} ({file_info['metadata']['size']} bytes)\nFile hash - {file_hash}")
            print("Available from peers:")
            for i, peer in enumerate(list(file_info['peers'].keys()), start=1):
                print(f"    {i}. {peer}")
        print("\nType 'refresh' to update this list, or 'exit' to quit.")

    def terminal_command_loop(self, file_manager):
        while True:
            command = input("Enter command (refresh, download): ").strip().lower()
            if command == "refresh":
                file_manager.refresh()
            elif command == "download":
                self.select_file()
            else:
                print("Unknown command.")

    def select_file(self):
        file_hash = input("Enter the hash of the file you want to download: ")
        selected_file = self.peer_indexer.get_peer_index().get(file_hash)
        if selected_file:
            logging.info(f"Selected file: {selected_file['metadata']['name']} ({selected_file['metadata']['size']} bytes)")
            logging.info(f"Starting download for file hash {file_hash}.")
            self.download_and_verify_file(file_hash, selected_file)
            if self.download_and_verify_file == True:
                self.clear_temp_storage(file_hash)
            else :
                logging.error(f"Error downloading file with hash {file_hash}.")
                return None
        else:
            logging.error(f"File with hash {file_hash} not found in peer index.")

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
            elif action == "file_request": 
                self.handle_file_request(data, addr[0])
            elif action == "file_chunk":
                self.handle_received_chunk(data, addr[0])
            logging.info(f"Handled received message from {addr}")
        except Exception as e:
            logging.error(f"Error handling received message from {addr}: {e}")

    def refresh(self):
        print("Update is detected, refreshing...")
        self.peer_indexer.load_peer_index()
        self.display_terminal()

    def handle_file_request(self, file_request, peer_address):
        try: 
            file_hash = file_request["data"]["file_hash"]
            bit_offset = file_request["data"]["bit_offset"]
            chunk_size = file_request["data"]["chunk_size"]
            sequence_number = file_request["data"]["chunk_sequence_number"]
            file_path = self.local_indexer.get_file_path(file_hash)
            with open(file_path, 'rb') as f:
                f.seek(bit_offset)
                chunk = f.read(chunk_size)

            self.peer.send_file_chunk(peer_address, self.format_message("file_chunk", chunk_info = {
                "file_hash": file_hash,
                "chunk_size": chunk_size,
                "chunk_sequence_number": sequence_number,
                "chunk_data": chunk
            })) # need to implement this method in peer, takes a peer address, chunk data, file hash and sequence number as arguments
            logging.info(f"Sent file chunk from bit: {bit_offset} to {bit_offset+chunk_size} to address: {peer_address}")
        except Exception as e:
            logging.error(f"Error handling file request: {e}")

    def handle_received_chunk(self, data, addr):
        chunk_info = json.loads(data)
        chunk_data = chunk_info["data"]["data"]
        file_hash = chunk_info["data"]["file_hash"]
        chunk_size = chunk_size["data"]["chunk_size"]
        chunk_sequence = chunk_info["data"]["chunk_sequence_number"]

        if file_hash not in self.temp_file_storage:
            self.temp_file_storage[file_hash] = {}
        
        self.temp_file_storage[file_hash][chunk_sequence] = chunk_data
        
    def download_file_chunks(self, file_hash, file_size):
        size = file_size
        chunk_size = 1024
        num_chunks = (size // chunk_size) + (1 if size % chunk_size != 0 else 0)
        chunks = [None] * num_chunks
        chunk_attempts = [set() for _ in range(num_chunks)]
        peers_with_file = self.peer_indexer.get_file_peers(file_hash)

        def request_chunk(i):
            available_peers = set(peers_with_file.keys()) - chunk_attempts[i]
            if not available_peers:
                return False
            chosen_peer = random.choice(list(available_peers))
            self.peer.send_file_request(chosen_peer, self.format_message("file_request",{
                "file_hash": file_hash,
                "bit_offset": i * chunk_size,
                "chunk_size": chunk_size if i < num_chunks - 1 else size - i * chunk_size,
                "chunk_sequence_number": i
            })) # need to implement this method in peer, takes a peer address and message as arguments
            chunk_attempts[i].add(chosen_peer)
            return True

        max_attempts = len(peers_with_file)  # Allow as many attempts as there are peers
        while None in chunks:
            time.sleep(1)
            for i in range(num_chunks):
                if chunks[i] is None:
                    if len(chunk_attempts[i]) >= max_attempts:
                        logging.error(f"Failed to download chunk {i} after {max_attempts} attempts.")
                        continue
                    if not request_chunk(i):
                        logging.info(f"No available peers left to try for chunk {i}.")
                        continue
                else:
                    chunks[i] = self.temp_file_storage[file_hash].get(i)

        if all(chunk is not None for chunk in chunks):
            return b''.join(chunks)
        else:
            return None

    def download_and_verify_file(self, file_hash, selected_file):
            self.logger.info(f"Attempt to download and verify file: {selected_file['metadata']['name']}")
            try:
                reconstructed_file = self.download_file_chunks(file_hash, selected_file["metadata"]["size"])
                if reconstructed_file:
                    if self.verify_file(file_hash, reconstructed_file):
                        self.save_file(selected_file["metadata"]["name"], reconstructed_file)
                        self.logger.info("File downloaded, verified and saved successfully.")
                        return True
                    else:
                        self.logger.warning("Verification failed, downloaded file does not match the original.")
                        return False
                else:
                    self.logger.warning("Failed to download file.")
                    return False
            except Exception as e:
                self.logger.error(f"Exception during file download/verification: {e}")

    def verify_file(self, file_hash, data):
            try:
                self.logger.debug(f"Starting file verification for hash: {file_hash}")
                hasher = hashlib.sha256()
                hasher.update(data)
                calculated_hash = hasher.hexdigest()

                if file_hash == calculated_hash:
                    self.logger.info(f"File hash verified successfully for {file_hash}")
                    return True
                else:
                    self.logger.warning(f"Hash mismatch: expected {file_hash}, got {calculated_hash}")
                    return False
            except Exception as e:
                self.logger.error(f"Error verifying file hash for {file_hash}: {str(e)}")
                return False
        
    def clear_temp_storage(self, file_hash):
        if file_hash in self.temp_file_storage:
            del self.temp_file_storage[file_hash] 
            logging.info(f"Temporary storage cleared for file hash {file_hash}")

    def save_file(self, file_name, data):
        try:
            file_path = os.path.join(self.shared_folder, file_name)
            with open(file_path, 'wb') as f:
                f.write(data)
            logging.info(f"File saved successfully: {file_name}")
        except Exception as e:
            logging.error(f"Error saving file: {e}")

    def create_update_message(self, action, file_hash, metadata=None):
        """Create a message to update peers about a file index change."""
        message = {
            "action": action,
            "file_hash": file_hash
        }
        if metadata:
            message["metadata"] = metadata
        return message
