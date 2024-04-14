from django.urls import path
from django.urls import include, path

from . import views

urlpatterns = [
    path('', views.index),

    path('get-network-files/', views.get_network_files_async, name='get_network_files'),
    path('get-my-files/', views.get_my_files_async, name='get_my_files'),
    path('get-active-peers/', views.get_peers_async, name='get_active_peers'),
]
