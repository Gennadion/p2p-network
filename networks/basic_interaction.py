from socket import *
import time
import threading
import os

bcast = "10.203.255.255"
me = None
peers = {}
port = 9613
mes = b'Imma here!'
pref = b'Gimme dat!'
key = os.urandom(256)

def broadcast():
  while True:
    s = socket(AF_INET, SOCK_DGRAM)
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    s.sendto(mes + key, (bcast, port))
    s.close()
    time.sleep(1)

def request():
  while True:
    prompt = input().encode('utf-8')
    for addr in peers:
      other_key = peers[addr]
      s = socket(AF_INET, SOCK_DGRAM)
      s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
      enc = bytes([prompt[i] ^ key[i] ^ other_key[i] for i in range(len(prompt))])
      s.sendto(pref + enc, (addr, port))
      s.close()

def record():
  global me
  while True:
    s = socket(AF_INET, SOCK_DGRAM)
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    s.bind((bcast, port))
    data, addr = s.recvfrom(1024)
    if data[:10] == b'Imma here!':
      if addr[0] != me:
        if data[10:] == key:
          me = addr[0]
        else:
          peers[addr[0]] = data[10:]
    s.close()

def receive():
  while True:
    if me:
      s = socket(AF_INET, SOCK_DGRAM)
      s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
      s.bind((me, port))
      data, addr = s.recvfrom(1024)
      if data[:10] == b'Gimme dat!':
        message = data[10:]
        if addr[0] in peers:
          other_key = peers[addr[0]]
          if addr[0] != me:
            enc = bytes([message[i] ^ key[i] ^ other_key[i] for i in range(len(message))])
            print(f"{enc.decode('utf-8')} from {addr[0]}")
      s.close()


br_thread = threading.Thread(target=broadcast)
rec_thread = threading.Thread(target=record)
req_thread = threading.Thread(target=request)
reci_thread = threading.Thread(target=receive)
br_thread.start()
rec_thread.start()
req_thread.start()
reci_thread.start()
