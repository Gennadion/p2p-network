import os

def encrypt(key, message):
    return bytes([message[i] ^ key[i] for i in range(len(message))])
decrypt = encrypt
def create_key():
    return os.urandom(256)