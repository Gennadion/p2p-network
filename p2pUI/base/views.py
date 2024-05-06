import asyncio
import json
import random
import threading
import time

from django.shortcuts import render
from asgiref.sync import sync_to_async

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


network_files = [FileModel("test", 1024, "hash1", "peer 1")]
active_peers = [Peer(123, 12, 8000, "active_peer_1")]


# Function to continuously update network files
def update_network_files():
    global network_files
    while True:
        # Generating new network files
        # Update the shared data structure

        # Sleep for some time
        time.sleep(10)


def update_active_peers():
    global active_peers
    while True:
        # Generate random peer names
        # Update the shared data structure
        # Sleep for some time
        time.sleep(10)


# Create a separate thread for updating network files
update_thread = threading.Thread(target=update_network_files)
update_thread.daemon = True  # Daemonize the thread, so it stops when the main thread exits
update_thread.start()

# Create a separate thread for updating active peers
update_thread = threading.Thread(target=update_active_peers)
update_thread.daemon = True  # Daemonize the thread, so it stops when the main thread exits
update_thread.start()


# helper funcs
async def get_network_files_async(request):
    print('prepare to get files on network')
    # Get the current state of network files (snapshot)
    current_files = network_files.copy()
    serialized_files = [file.to_dict() for file in current_files]

    return JsonResponse({'net_files': serialized_files})


async def get_my_files_async(request):
    print('prepare to get files on localhost')
    await asyncio.sleep(2)
    my_files = ["My file 1", "My file 2"]
    return JsonResponse({'my_files': my_files})


async def get_peers_async(request):
    print('prepare to get active peers')
    # Get the current state of active peers (snapshot)
    current_peers = active_peers.copy()
    serialized_peers = [peer.to_dict() for peer in current_peers]
    return JsonResponse({'active_peers': serialized_peers})


async def index(request):
    await asyncio.sleep(1)
    return render(request, 'base/index.html')


async def index_disconnected(request):
    await asyncio.sleep(1)
    return render(request, 'base/index_disconnected.html')
