import asyncio

from django.shortcuts import render
from asgiref.sync import sync_to_async

# Create your views here.
from django.http import HttpResponse, JsonResponse


# helper funcs
async def get_network_files_async(request):
    print('prepare to get files on network')
    await asyncio.sleep(2)

    net_files = ["File Name 1", "File Name 2", "File Name 3", "File Name 4", "File Name 5", "File Name 6",
                 "File Name 7", "File Name 8", "File Name 9", "File Name 10", "File Name 11", "File Name 12"]
    return JsonResponse({'net_files': net_files})

async def get_my_files_async(request):
    print('prepare to get files on localhost')
    await asyncio.sleep(2)
    my_files = ["My file 1", "My file 2"]
    return JsonResponse({'my_files': my_files})



async def get_peers_async(request):
    print('prepare to get active peers')
    await asyncio.sleep(2)

    active_peers = ['peer1', 'peer2', 'peer3']  # Replace with actual data retrieval
    # active_peers = []  # Replace with actual data retrieval
    return JsonResponse({'active_peers': active_peers})


async def index(request):





    return render(request, 'base/index.html')
