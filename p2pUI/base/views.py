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


class Peer:
    def __init__(self, peer_id, ip_address, port, username):
        self.peer_id = peer_id
        self.ip_address = ip_address
        self.port = port
        self.username = username

    def to_dict(self):
        return {
            "username": self.username,
            "port": self.port,
            "ip_address": self.ip_address,
            "peer_id": self.peer_id
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
        time.sleep(1)


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
    print('prepare to get files on network')
    # Get the current state of network files (snapshot)
    # serialized_files = [file for file in network_files]
    return JsonResponse(network_files, safe=False)


async def get_local_files_async(request):
    global local_files
    print('prepare to get files on localhost')
    time.sleep(2)
    # serialized_files = [file for file in local_files]

    return JsonResponse(local_files, safe=False)


async def get_peers_async(request):
    global active_peers
    print('prepare to get active peers')
    # Get the current state of active peers (snapshot)
    # serialized_peers = [peer for peer in active_peers]
    return JsonResponse(active_peers, safe=False)


def initialize_node():
    # alexarlord-boop setup
    shared_folder = '../../Desktop/p2p'
    local_address = "192.168.96.0"
    mask = "255.255.224.0"
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


    # Create a separate thread for updating local files for each node
    update_thread = threading.Thread(target=update_local_files, args=(node,))
    update_thread.daemon = True  # Daemonize the thread, so it stops when the main thread exits
    update_thread.start()

    # Create a separate thread for updating network files for each node
    update_thread = threading.Thread(target=update_network_files, args=(node,))
    update_thread.daemon = True  # Daemonize the thread, so it stops when the main thread exits
    update_thread.start()

    # Create a separate thread for updating active peers for each node
    update_thread = threading.Thread(target=update_active_peers, args=(node,))
    update_thread.daemon = True  # Daemonize the thread, so it stops when the main thread exits
    update_thread.start()

    node.run_forever()


async def index(request):
    # Initialize and run the Node in a separate thread
    node_thread = threading.Thread(target=initialize_node)
    node_thread.start()

    await asyncio.sleep(1)

    return render(request, 'base/index.html')


async def index_disconnected(request):
    await asyncio.sleep(1)
    return render(request, 'base/index_disconnected.html')
