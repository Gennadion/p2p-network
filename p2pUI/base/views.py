import asyncio
import threading
import time
import logging

from .backend.Node import Node

from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse, JsonResponse


class FileModel:
    def __init__(self, filename: str, size: int, hash: str, origin):
        self.filename = filename
        self.size = size
        self.hash = hash
        self.origin = origin

    def to_dict(self):
        return {
            "name": self.filename,
            "size": self.size,
            "hash": self.hash,
            "origin": self.origin
        }


local_files = []
network_files = []
active_peers = []


# Function to continuously update local files
def update_local_files(node):
    global local_files
    while True:
        # Update the shared data structure
        local_files = node.get_local_files()

        # Sleep for some time
        time.sleep(3)


# Function to continuously update network files
def update_network_files(node):
    global network_files
    while True:
        # Update the shared data structure
        network_files = node.get_net_files()
        # Sleep for some time
        time.sleep(3)


def update_active_peers(node):
    global active_peers
    while True:
        # Update the shared data structure
        active_peers = node.get_active_peers()
        # Sleep for some time
        time.sleep(3)


# helper funcs
async def get_network_files_async(request):
    global network_files
    time.sleep(3)
    return JsonResponse(network_files, safe=False)


async def get_local_files_async(request):
    global local_files
    time.sleep(1)
    return JsonResponse(local_files, safe=False)


async def get_peers_async(request):
    global active_peers

    active_peers_str = []
    for item in active_peers:
        if isinstance(item, bytes):
            item = item.decode('utf-8')
        active_peers_str.append(item)

    return JsonResponse(active_peers_str, safe=False)



node_initialized = False
initialized_node: Node = None


def initialize_node():
    global node_initialized, initialized_node
    logging.basicConfig(filename="std.log", filemode="a", level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # alexarlord-boop setup
    shared_folder = '../../Desktop/p2p'
    local_address = "172.20.10.0"
    mask = "255.255.255.240"
    port = 9613

    index_file_name = '../../index.json'
    peer_index_file_name = '../../peer_index.json'

    if not node_initialized:
        node = Node(
            local_address,
            mask,
            shared_folder,
            index_file_name,
            peer_index_file_name,
            port=port
        )
        node.run()
        node_initialized = True
        initialized_node = node

        # Create a separate thread for updating local files for each node
        update_thread1 = threading.Thread(target=update_local_files, args=(node,))
        update_thread1.daemon = True  # Daemonize the thread, so it stops when the main thread exits
        update_thread1.start()

        # Create a separate thread for updating network files for each node
        update_thread2 = threading.Thread(target=update_network_files, args=(node,))
        update_thread2.daemon = True  # Daemonize the thread, so it stops when the main thread exits
        update_thread2.start()
        #
        # Create a separate thread for updating active peers for each node
        update_thread3 = threading.Thread(target=update_active_peers, args=(node,))
        update_thread3.daemon = True  # Daemonize the thread, so it stops when the main thread exits
        update_thread3.start()


async def index(request):
    # Initialize and run the Node in a separate thread
    # node_thread = threading.Thread(target=initialize_node)
    # node_thread.start()

    initialize_node()

    return render(request, 'base/index.html')


async def index_disconnected(request):
    global node_initialized, initialized_node

    if initialized_node:
        node_initialized = False
        initialized_node.stop()
    return render(request, 'base/index_disconnected.html')
