from socket import *
import logging
from networks.encryption import create_key


class Messager:
    logging.basicConfig(filename="std.log", filemode="a", level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def __init__(self, addr, mask, port=9613, me=None):
        self.logger = logging.getLogger(__name__)
        logging.info(f"Initializing Messager for {me} at {addr}:{port}")
        self.me = me
        self.addr = addr
        self.port = port
        self.bcast = '.'.join(list(map(str, [int(a) | (255 ^ int(m)) for a, m in zip(addr.split('.'), mask.split('.'))])))
        self.key, self.pkey = create_key()

    def broadcast(self, message):
        logging.info(f"Broadcasting message to {self.bcast}...")
        try:
            s = socket(AF_INET, SOCK_DGRAM)
            s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            s.sendto(message, (self.bcast, self.port))
        except Exception as e:
            logging.error(f"Error broadcasting message: {e}")
        finally:
            s.close()

    def send(self, addr, message):
        logging.info(f"Sending message to {addr}...")
        try:
            s = socket(AF_INET, SOCK_STREAM)
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.connect((addr, self.port))
            s.sendall(message)
            print(f"I sent: {message} to {addr}")
        except Exception as e:
            logging.error(f"Error sending message to {addr}: {e}")
        finally:
            s.close()

    def record(self):
        logging.info("Recording incoming broadcast...")
        try:
            s = socket(AF_INET, SOCK_DGRAM)
            s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.bind((self.bcast, self.port))
            data, addr = s.recvfrom(32768)
            logging.debug(f"Received data from {addr}")
            s.close()
            return data, addr
        except Exception as e:
            logging.error(f"Error recording incoming broadcast: {e}")

    def receive(self):
        logging.info("Receiving direct message...")
        try:
            s = socket(AF_INET, SOCK_STREAM)
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.bind((self.me, self.port))
            s.listen()
            conn, addr = s.accept()
            data = []
            batch = conn.recv(1024)
            data.append(batch)
            while batch:
                batch = conn.recv(1024)
                data.append(batch)
            message = b''.join(data)
            s.close()
            return message, addr
        except Exception as e:
            logging.error(f"Error receiving direct message: {e}")
