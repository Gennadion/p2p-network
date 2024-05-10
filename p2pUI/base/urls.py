from django.urls import path
from django.urls import include, path

from . import views

urlpatterns = [
    path('', views.index_disconnected),
    path('connect/', views.index),

    path('get-network-files/', views.get_network_files_async, name='get_network_files'),
    path('get-local-files/', views.get_local_files_async, name='get_local_files'),
    path('get-active-peers/', views.get_peers_async, name='get_active_peers'),
]
