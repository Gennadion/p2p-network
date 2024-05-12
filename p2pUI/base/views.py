import asyncio
import json
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
active_peers = {}
downloading_files = []


# Function to continuously update local files
def update_local_files(node):
    global local_files
    while True:
        # Update the shared data structure
        local_files = node.get_local_files()

        time.sleep(1)


# Function to continuously update network files
def update_network_files(node):
    global network_files
    while True:
        # Update the shared data structure
        network_files = node.get_net_files()
        time.sleep(1)


def update_active_peers(node):
    global active_peers
    while True:
        # Update the shared data structure
        active_peers = node.get_active_peers()
        time.sleep(1)


initialized_node: Node = None
init_lock = threading.Lock()  # Lock for thread safety during initialization


# helper funcs
async def get_downloading_files_async(request):
    global downloading_files
    return JsonResponse({"downloading": downloading_files})


async def get_file_async(request, file_hash, file_name):
    global downloading_files
    if file_name not in downloading_files:
        downloading_files.append(file_name)
    if initialized_node is not None:
        with init_lock:
            try:
                event = {"file_hash": file_hash}
                initialized_node.request_file(event=event)
                downloading_files.remove(file_name)
                return HttpResponse(file_name + " is saved and verified")
            except Exception as e:
                return HttpResponse(file_name + " download failed")
    else:
        return HttpResponse("Node is not initialized.")


# async def get_download_status_async(request):
#     if initialized_node is not None:
#         with init_lock:
#             return JsonResponse(initialized_node.get_downloading())
#     else:
#         return HttpResponse("Node is not initialized.")


async def get_network_files_async(request):
    global network_files
    time.sleep(1)

    return JsonResponse(network_files, safe=False)


async def get_local_files_async(request):
    global local_files
    time.sleep(2)
    return JsonResponse(local_files, safe=False)


async def get_peers_async(request):
    global active_peers
    try:
        # Convert bytes data to string representation
        for peer in active_peers['active_peers']:
            peer['key'] = peer['key'].decode('utf-8') if isinstance(peer['key'], bytes) else str(peer['key'])
    except TypeError:
        pass
    serialized_peers = json.dumps(active_peers)
    time.sleep(1)
    return JsonResponse(serialized_peers, safe=False)


def initialize_node():
    global initialized_node
    logging.basicConfig(filename="std.log", filemode="a", level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # alexarlord-boop setup
    shared_folder = '../../Desktop/p2p'
    local_address = "172.20.10.0"
    mask = "255.255.255.240"
    port = 9613

    index_file_name = '../../index.json'
    peer_index_file_name = '../../peer_index.json'

    node = Node(
        local_address,
        mask,
        shared_folder,
        index_file_name,
        peer_index_file_name,
        port=port
    )
    node.run()

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

    init_thread = threading.Thread(target=initialize_node)
    init_thread.start()

    return render(request, 'base/index.html')


async def index_disconnected(request):
    global initialized_node

    if initialized_node:
        try:
            initialized_node.stop()
        except Exception as e:
            print(e)
    return render(request, 'base/index_disconnected.html')
