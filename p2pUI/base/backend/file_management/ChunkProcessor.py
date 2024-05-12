import hashlib
import logging
import time
import random

CHUNK_SIZE = 1024


class ChunkProcessor:
    logging.basicConfig(filename="std.log", filemode="a", level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def __init__(self, node, file_hash, selected_file):
        self.name = selected_file["name"]
        self.size = selected_file["size"]
        self.num_chunks = (self.size // CHUNK_SIZE) + (1 if self.size % CHUNK_SIZE != 0 else 0)
        self.chunks = [None] * self.num_chunks
        self.node = node
        self.temp_file_storage = {}
        self.logger = logging.getLogger(__name__)
        self.chunk_attempts = [set() for _ in range(self.num_chunks)]
        self.max_attempts = 0
        self.file_hash = file_hash
        self.peers_with_file = {}
        logging.info(f"Initializing ChunkProcessor")

    def handle_chunk(self, chunk_info):
        chunk_data = chunk_info["chunk_data"]
        file_hash = chunk_info["file_hash"]
        chunk_sequence = chunk_info["chunk_sequence_number"]

        if file_hash not in self.temp_file_storage:
            self.temp_file_storage[file_hash] = {}

        self.chunks[chunk_sequence] = chunk_data
        self.temp_file_storage[file_hash][chunk_sequence] = chunk_data
        logging.info(f"Saved chunk {chunk_sequence}")

    def request_chunk(self, i):
        if len(self.chunk_attempts[i]) >= self.max_attempts:
            logging.error(f"Failed to download chunk {i} after {self.max_attempts} attempts.")
            return False
        available_peers = set(self.peers_with_file.keys()) - self.chunk_attempts[i]
        chosen_peer = random.choice(list(available_peers))
        if not available_peers:
            logging.info(f"No available peers left to try for chunk {i}.")
            return False
        event = {
            "action": "request_chunk",
            "peer_address": chosen_peer,
            "file_hash": self.file_hash,
            "bit_offset": i * CHUNK_SIZE,
            "chunk_size": CHUNK_SIZE if i < self.num_chunks - 1 else self.size - i * CHUNK_SIZE,
            "chunk_sequence_number": i
        }
        self.node.handle_event(event)
        self.chunk_attempts[i].add(chosen_peer)
        return True

    def download_file_chunks(self):
        self.peers_with_file = self.node.get_file_peers(self.file_hash)
        self.max_attempts = len(self.peers_with_file)  # Allow as many attempts as there are peers
        timeout_achieved = False
        while None in self.chunks and not timeout_achieved:
            time.sleep(1)
            for i in range(self.num_chunks):
                if self.chunks[i] is None:
                    self.request_chunk(i)

        if all(chunk is not None for chunk in self.chunks):
            return b''.join(self.chunks)
        else:
            return None

    def verify_file(self, data):
        try:
            self.logger.debug(f"Starting file verification for hash: {self.file_hash}")
            hasher = hashlib.sha256()
            hasher.update(data)
            calculated_hash = hasher.hexdigest()
            if self.file_hash == calculated_hash:
                self.logger.info(f"File hash verified successfully for {self.file_hash}")
                return True
            self.logger.warning(f"Hash mismatch: expected {self.file_hash}, got {calculated_hash}")
            return False
        except Exception as e:
            self.logger.error(f"Error verifying file hash for {self.file_hash}: {str(e)}")
            return False

    def download_and_verify_file(self):
        self.logger.info(f"Attempt to download and verify file: {self.name}")
        try:
            reconstructed_file = self.download_file_chunks()
            if reconstructed_file:
                if self.verify_file(reconstructed_file):
                    event = {
                        "action": "save_file",
                        "name": self.name,
                        "data": reconstructed_file
                    }
                    self.node.handle_event(event)
                    self.logger.info("File downloaded, verified and saved successfully.")
                    return True
                self.logger.warning("Verification failed, downloaded file does not match the original.")
                return False
            self.logger.warning("Failed to download file.")
            return False
        except Exception as e:
            self.logger.error(f"Exception during file download/verification: {e}")
