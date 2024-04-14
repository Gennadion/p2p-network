import threading
from file_management.Indexer import LocalIndexManager, PeerIndexManager
from file_management.Overwatcher import DirectoryMonitor
from file_management.FileManager import FileManager
from networks.peer import Peer 
from networks.messager import Messager
import logging 

def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    shared_folder = 'C:\\FileTransfers'
    local_address = "192.168.230.4"
    mask = "255.255.255.0"
    port = 9613

    index_file_name = 'index.json'
    peer_index_file_name = 'peer_index.json'

    local_index_manager = LocalIndexManager(shared_folder, index_file_name)
    local_index_manager.index_files()

    peer_index_manager = PeerIndexManager(peer_index_file_name)
    peer_index_manager.load_peer_index()
    
    messenger = Messager(addr=local_address, mask=mask, port=port, me=local_address)

    file_manager = FileManager(shared_folder, index_file_name, peer_index_file_name, local_indexer=local_index_manager, peer_indexer=peer_index_manager)

    peer = Peer(addr=local_address, mask=mask, port=port, file_manager=file_manager, messager=messenger)
    file_manager.peer = peer  

    peer_thread = threading.Thread(target=peer.start, daemon=True)
    peer_thread.start()

    directory_monitor = DirectoryMonitor(shared_folder, local_index_manager, file_manager)
    directory_monitor_thread = threading.Thread(target=directory_monitor.start, daemon=True)
    directory_monitor_thread.start()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        logging.info("Shutting down P2P client...")
        directory_monitor.stop()
        peer_index_manager.clear_peer_index()
        local_index_manager.clear_local_index()
        peer.stop()

if __name__ == "__main__":
    main()
