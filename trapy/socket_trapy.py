import socket
import logging

from .utils import parse_address

logger = logging.getLogger(__name__)


class Conn:
    def __init__(self, sock=None):
        if sock is None:
            sock = socket.socket()
            
        self.socket = sock


class ConnException(Exception):
    pass


def listen(address):
    print("listen(f'{address}'):")
    conn = Conn()

    host, port = parse_address(address)

    logger.info(f'socket binded to {address}')
    conn.socket.bind((host, port))
    conn.socket.listen(1)
    
    return conn


def accept(conn):
    print("accept")
    sock, _ = conn.socket.accept()

    return Conn(sock)


def dial(address):
    print("dial(f'{address}'):")
    conn = Conn()

    host, port = parse_address(address)

    conn.socket.connect((host, port))

    return conn


def send(conn: Conn, data):
    print("send({data}):")
    return conn.socket.send(data)


def recv(conn: Conn, length):
    print("recv({length}):")
    return conn.socket.recv(length)


def close(conn: Conn):
    conn.socket.close()
    conn.socket = None
