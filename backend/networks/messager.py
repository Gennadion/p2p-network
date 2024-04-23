from socket import *
import logging

class Messager:
    logging.basicConfig(filename="std.log", filemode="a", level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    def __init__(self, addr, mask, port=9613, me=None):
        self.logger = logging.getLogger(__name__)
        logging.info(f"Initializing Messager for {me} at {addr}:{port}")
        self.me = me
        self.addr = addr
        self.port = port
        self.port_direct = port + 1
        self.bcast = '.'.join(list(map(str, [int(a) | (255 ^ int(m)) for a, m in zip(addr.split('.'), mask.split('.'))])))

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
            s.connect((addr, self.port_direct))
            s.sendall(message)
        except Exception as e:
            logging.error(f"Error sending message to {addr}: {e}")
        finally:
            s.close()

    def record(self):
        logging.info("Recording incoming broadcast...")
        try:
            s = socket(AF_INET, SOCK_DGRAM)
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.bind((self.addr, self.port))
            data, addr = s.recvfrom(32768)
            logging.debug(f"Received data from {addr}")
            return data, addr
        except Exception as e:
            logging.error("Error recording incoming broadcast: {e}")
        finally:
            if s:
                s.close()

    def receive(self):
        logging.info("Receiving direct message...")
        try:
            s = socket(AF_INET, SOCK_STREAM)
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.bind((self.me, self.port_direct))
            s.listen()
            conn, addr = s.accept()
            data = b""
            while True:
                batch = conn.recv(1024)
                if not batch:
                    break
                data += batch
            return data, addr
        except Exception as e:
            logging.error("Error receiving direct message: {e}")
        finally:
            conn.close()
