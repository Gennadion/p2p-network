import logging
from Node import Node


def main():
    logging.basicConfig(filename="std.log", filemode="a", level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    shared_folder = 'C:\\FileTransfers'
    local_address = "192.168.230.4"
    mask = "255.255.255.0"
    port = 9613

    index_file_name = 'index.json'
    peer_index_file_name = 'peer_index.json'

    node = Node(
        local_address,
        mask,
        shared_folder,
        index_file_name,
        peer_index_file_name,
        port,
        me=local_address
    )
    node.run_forever()


if __name__ == "__main__":
    main()
