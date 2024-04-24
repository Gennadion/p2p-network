from Overwatcher import *
import logging
import os


def create_update_message(action, file_hash, metadata=None):
    """Create a message to update peers about a file index change."""
    message = {
        "action": action,
        "file_hash": file_hash
    }
    if metadata:
        message["metadata"] = metadata
    return message


def format_update(keyword, file_hash, metadata=None):
    event = {
        "action": keyword,
        "file_hash": file_hash,
        "metadata": metadata
    }
    return event


class FileManager:
    logging.basicConfig(filename="std.log", filemode="a", level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def __init__(self, node, shared_folder, local_indexer=None):
        self.node = node
        self.logger = logging.getLogger(__name__)
        logging.info(f"Initializing FileManager for {shared_folder}")
        self.shared_folder = shared_folder
        self.local_indexer = local_indexer
        self.directory_monitor = DirectoryMonitor(shared_folder, local_indexer, self)

    def get_full_index(self):
        local_index_file = self.local_indexer.get_index()
        index_to_send = {}
        for file_hash, metadata in local_index_file.items():
            filtered_metadata = {"name": metadata["name"], "size": metadata["size"]}
            index_to_send[file_hash] = filtered_metadata
        return index_to_send

    def get_file_data(self, file_path):
        file_hash, file_metadata = self.local_indexer.add_index_to_json(file_path)
        filtered_metadata = {
            "name": file_metadata["name"],
            "size": file_metadata["size"]
        }
        update_message = create_update_message("add", file_hash, filtered_metadata)
        return update_message

    def get_file_path(self, file_hash):
        local_index = self.local_indexer.get_index()
        path = local_index[file_hash]["path"]
        return path

    def save_file(self, file_name, data):
        try:
            file_path = os.path.join(self.shared_folder, file_name)
            with open(file_path, 'wb') as f:
                f.write(data)
            logging.info(f"File saved successfully: {file_name}")
        except Exception as e:
            logging.error(f"Error saving file: {e}")

    def clear_indices(self):
        self.local_indexer.clear_local_index()

    def share_file_index(self, file_path):
        """Share a newly added file index with peers, only including the filename and size in the metadata."""
        try:
            file_hash, file_metadata = self.local_indexer.add_index_to_json(file_path)
            filtered_metadata = {
                "name": file_metadata["name"],
                "size": file_metadata["size"]
            }
            update_message = create_update_message("add", file_hash, filtered_metadata)
            event = {
                "action": "send_file_update",
                "update": update_message
            }
            self.node.handle_event(event)
            logging.info(f"Shared file index for {file_path} with peers.")
        except Exception as e:
            logging.error(f"Error sharing file index for {file_path}: {e}")

    def unshare_file_index(self, file_path):
        """Unshare a file index with peers."""
        try:
            file_hash = self.local_indexer.delete_index_from_json(file_path)
            update_message = create_update_message("delete", file_hash)
            event = {
                "action": "send_file_update",
                "update": update_message
            }
            self.node.handle_event(event)
            logging.info(f"Unshared file index for {file_path}")
        except Exception as e:
            logging.error(f"Error unsharing file index for {file_path}: {e}")
