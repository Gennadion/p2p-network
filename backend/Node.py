import json
import threading
from old_networks.peer import Peer
from file_management.FileManager import FileManager
from file_management.LocalIndexManager import *
from file_management.Overwatcher import *


class Node:
    def __init__(self,
                 addr,
                 mask,
                 shared_folder,
                 index_file_name='index.json',
                 peer_index_file_name='peer_index.json',
                 port=9613,
                 me=None
                ):
        self.peer = Peer(self, addr, mask, port, me)

        local_indexer = LocalIndexManager(shared_folder, index_file_name)
        local_indexer.index_files()

        peer_indexer = PeerIndexManager(peer_index_file_name)
        peer_indexer.load_peer_index()

        self.file_manager = FileManager(self, shared_folder, local_indexer, peer_indexer)

        self.directory_monitor = DirectoryMonitor(shared_folder, local_indexer, self.file_manager)

        jobs = [
            self.peer.start,
            self.directory_monitor.start
        ]

        self.threads = map(lambda job: threading.Thread(target=job, daemon=True), jobs)

        self.event_dictionary = {
            "new_peer": self.handle_new_peer,
            "send_file_update": self.send_file_update
        }

    def run(self):
        for thread in self.threads:
            thread.start()

    def stop(self):
        logging.info("Shutting down P2P client...")
        self.directory_monitor.stop()
        self.file_manager.clear_indices()
        self.peer.stop()
        self.file_manager.refresh()
        for thread in self.threads:
            thread.join(timeout=2)

    def run_forever(self):
        self.run()
        try:
            while True:
                pass
        except KeyboardInterrupt:
            self.stop()

    def handle_new_peer(self, event):
        addr = event["addr"]
        my_file_index = self.file_manager.get_full_index()
        my_file_index_bytes = json.dumps(my_file_index)
        self.peer.send_index(addr, my_file_index_bytes)

    def send_file_update(self, event):
        update_bytes = json.dumps(event["update"])
        self.peer.send_updates(update_bytes)

    def handle_event(self, event):
        self.event_dictionary[event["action"]](event)


