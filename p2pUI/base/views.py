import asyncio
import json
import random
import threading
import time

from django.shortcuts import render
from asgiref.sync import sync_to_async

# Create your views here.
from django.http import HttpResponse, JsonResponse


# Shared data structure to store network files
class NetworkFile:

    def __init__(self, name, acquired=False):
        self.name = name
        self.acquired = acquired

    def to_dict(self):
        return {
            'name': self.name,
            'acquired': self.acquired
        }


network_files = [NetworkFile("File Name 1"), NetworkFile("File Name 2", True)]
active_peers = ['peer1', 'peer2', 'peer3']


# Function to generate random peer names
def generate_random_peer_name():
    return f'peer_{random.randint(1, 100)}'


# Function to continuously update network files
def update_network_files():
    global network_files
    while True:
        # Simulate generating new network files
        new_files = [NetworkFile(name=f"New File {int(network_files[-1].name.split(' ')[-1]) + 1}")]
        # Update the shared data structure
        network_files.extend(new_files)
        # Sleep for some time
        time.sleep(30)


# Create a separate thread for updating network files
update_thread = threading.Thread(target=update_network_files)
update_thread.daemon = True  # Daemonize the thread, so it stops when the main thread exits
update_thread.start()


def update_active_peers():
    global active_peers
    while True:
        # Generate random number of peers (between 1 and 10)
        num_peers = random.randint(3, 3)
        # Generate random peer names
        new_peers = [generate_random_peer_name() for _ in range(num_peers)]
        # Update the shared data structure
        active_peers = new_peers
        # Sleep for some time
        time.sleep(3)


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
    return JsonResponse({'active_peers': current_peers})


async def index(request):
    await asyncio.sleep(1)
    return render(request, 'base/index.html')


async def index_disconnected(request):
    await asyncio.sleep(1)
    return render(request, 'base/index_disconnected.html')
