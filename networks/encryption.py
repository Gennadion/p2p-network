from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

def encrypt(key, message):
    publickey = RSA.import_key(key)
    cipher = PKCS1_OAEP.new(publickey)
    return cipher.encrypt(message)


def decrypt(key, message):
    cipher = PKCS1_OAEP.new(key)
    return cipher.decrypt(message)


def create_key():
    key = RSA.generate(4096, e=503223)
    public = key.publickey().export_key()
    return key, public