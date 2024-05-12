from django.urls import path
from django.urls import include, path

from . import views

urlpatterns = [
    path('', views.index_disconnected),
    path('connect/', views.index),

    path('get-network-files/', views.get_network_files_async, name='get_network_files'),
    path('get-local-files/', views.get_local_files_async, name='get_local_files'),
    path('get-active-peers/', views.get_peers_async, name='get_active_peers'),

    path('get-file/<str:file_hash>/<str:file_name>/', views.get_file_async, name='get_file_async'),
    # path('get-download-status/', views.get_download_status_async, name='get_download_status')
    path('get-downloading-files/', views.get_downloading_files_async, name='get_downloading_files')
]
