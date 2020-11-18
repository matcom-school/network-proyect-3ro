import socket
import logging
import time

from .protocol_tcp import Protocol_TCP
from .header_tcp import HeaderTCP
from .port_manager import ServerPortManager,ClientPortManager
from .utils import parse_address,wait_for 
from .mysocket import MySocket

logger = logging.getLogger(__name__)

class Conn:
    def __init__(self, myaddress, inner_header_tcp = None, ws = 1, ps = 1, top_try_conn = 3):
        self.inner_header_tcp = inner_header_tcp if not inner_header_tcp == None else HeaderTCP( source_port= myaddress[1])
        self.address = myaddress
        self.list_ack = []
        self.depot_list_msg = []
        self.list_msg = []
        self.windows_size_cache = ws
        self.windows_size = ws
        self.packet_size = ps
        self.pivot = 0
        self.list_chunk_data = []
        self.try_connection = 0
        self.top_try_conn = top_try_conn

    def demultiplexing( self, response: bytes) -> bool:
        source = HeaderTCP.get( HeaderTCP.KEYW_SOURCE, response)
        destination = HeaderTCP.get( HeaderTCP.KEYW_DESTINATION, response)

        return source == self.inner_header_tcp.destination_post and destination == self.inner_header_tcp.source_port

    def is_good_response(self, response, flacks = 0):
        result = not HeaderTCP.is_broken( response)
        result = result and self.demultiplexing( response)
        if flacks: 
            result = result and not HeaderTCP.get( HeaderTCP.KEYW_FLACKS, response ) & flacks == 0
        
        return result
    
    def reduce_frecuency(self):
        if not self.windows_size == 1:
            self.windows_size = self.windows_size - 1 
    
    def increase_frecuency(self):
        if self.windows_size < len(self.list_chunk_data) - self.pivot:
            self.windows_size = self.windows_size + 1 
    
    def send_and_wait_response(self, msg_to_send, flacks_to_checking , error_msg, do_answer = False):
        sender = MySocket( self.address ) 
        receiver = MySocket( self.address )
        for _ in range(5):
            sender.send( msg_to_send)
            try:
                wait_for(receiver.recv( blocking= False))
                if self.is_good_response( receiver.data, flacks_to_checking):
                    if do_answer:
                        responce = Protocol_TCP.map_flack_to_response( receiver.data ).compose()
                        sender.send( responce )
        
                    return receiver.data
            except TimeoutError:
                pass
        receiver.close()
        raise ConnException(error_msg)
            
    def recv_all_windows(self, receiver, lengh, windows_size, is_ack_wait, flacks_checking):
        timeout, recv_list = receiver.recv_all_windows(lengh, windows_size)
        if any(recv_list): self.try_connection = 0 
        else:
            if self.try_connection == self.top_try_conn: raise ConnException("Timeout for receiver packet connection down")
            self.try_connection += 1
            print(f"Timeout for receiver packet retry number {self.try_connection}")

        temp_list = []
        for packet in recv_list:
            if self.is_good_response( packet, flacks_checking ):
                ack = HeaderTCP.get( HeaderTCP.KEYW_SEQUENCE, packet )
                temp_list.append(packet)
                windows_size = HeaderTCP.get( HeaderTCP.KEYW_SIZE_W , packet )
                if not is_ack_wait:
                    if ack in self.list_ack:
                        self.inner_header_tcp.flacks |= Protocol_TCP.EFE
                    self.list_ack.append(ack)
            else: self.inner_header_tcp.flacks |= Protocol_TCP.EFE
        if timeout:
            self.inner_header_tcp.flacks |= Protocol_TCP.EFE
                
        return windows_size, temp_list

    def fraction_data(self,data):
        pivot = 0
        while True:
            try:
                self.list_chunk_data.append(data[pivot:pivot + self.packet_size]) 
            except IndexError:
                self.list_chunk_data.append(data[pivot:])
            pivot += self.packet_size
            if not len(data) > pivot: break
                
    def compose_msg_to_windows(self):
        if self.windows_size == 0:
            self.windows_size = self.windows_size_cache
        if self.windows_size > len(self.list_chunk_data) - self.pivot:
            self.windows_size_cache = self.windows_size - 1
            self.windows_size = len(self.list_chunk_data) - self.pivot 
        while len(self.list_msg) < self.windows_size:
            try:
                packet = Protocol_TCP.normal_sms(self.inner_header_tcp)
                packet.sequence_number += self.pivot + 1
                packet.windows_size = self.windows_size
                msg = packet.compose(self.list_chunk_data[self.pivot])
                self.list_ack.append(packet.sequence_number)
                self.pivot += 1
                self.list_msg.append(msg)
                self.depot_list_msg.append(msg)
            except IndexError:
                break
    
    def find_packet(self, _list: list, seq_num):
        for packet in _list:
           if seq_num == HeaderTCP.get(HeaderTCP.KEYW_SEQUENCE, packet):
               return packet



class ConnException(Exception):
    pass


def listen(address: str) -> Conn:
    host, port = parse_address(address)
    ServerPortManager().on( port )

    logger.info(f'socket binded to {address}')
    print(f'socket litsenig to {host}:{port}')
    
    conn = Conn((host,port))
    return conn

def accept(conn) -> Conn:
    socket = MySocket(conn.address)
    while True:
        msg = socket.recv()
        demultiplexing = conn.address[1] == HeaderTCP.get( HeaderTCP.KEYW_DESTINATION, msg )
        demultiplexing &= Protocol_TCP.SYS == HeaderTCP.get( HeaderTCP.KEYW_FLACKS, msg )
        if demultiplexing: break
    
    msg_header,_ = HeaderTCP.descompose(msg)
    print(f'socket blinder to {conn.address[0]}:{msg_header.source_port}')

    header_resp = Protocol_TCP.map_flack_to_response( msg_header)
    msg = header_resp.compose()
    conn = Conn( conn.address, header_resp)
    conn.inner_header_tcp.flacks = 0
    conn.inner_header_tcp.ack_number -= 1

    r = conn.send_and_wait_response( 
        msg_to_send = msg, 
        flacks_to_checking =  Protocol_TCP.SYS | Protocol_TCP.END,
        error_msg = f"ConnectingError Client not responce"
    )

    print("Connected !!!!!!!!")
    return conn

def dial(address) -> Conn:
    host, port = parse_address(address)
    my_port = ClientPortManager().get_free_port()
    
    header = Protocol_TCP.sys_wich((my_port,port))
    msg = header.compose()
    header.flacks = 0
    conn = Conn((host,my_port), header)

    logger.info(f'socket connecting to {address}')
    print(f'socket connecting to {host}:{port}')

    
    response = conn.send_and_wait_response( 
        msg_to_send = msg, 
        flacks_to_checking =  Protocol_TCP.SYS | Protocol_TCP.ACK,
        error_msg = f"ConnectingError Server {address} not responce",
        do_answer= True
    )

    print("Connected !!!!!!!!")
    header_resp,_ = HeaderTCP.descompose(response)
    conn.inner_header_tcp.ack_number = header_resp.sequence_number
    return conn


def send(conn: Conn, data: bytes) -> int:
    receiver = MySocket( conn.address )
    sender = MySocket( conn.address )

    conn.fraction_data(data)

    while True:
        conn.compose_msg_to_windows( )
        if not any(conn.list_ack) and not len(conn.list_chunk_data) > conn.pivot : break

        for msg in conn.list_msg:
            print(msg[16:])
            sender.send(msg)

        w_size, list_responce = conn.recv_all_windows( receiver, 0, conn.windows_size, True, Protocol_TCP.ACK)
        
        _reduce = not w_size == len(list_responce)
        for responce in list_responce:
            ack = HeaderTCP.get( HeaderTCP.KEYW_ACK, responce)
            if ack in conn.list_ack:
                packet = conn.find_packet( conn.list_msg, ack)
                conn.list_msg.remove( packet )
                conn.list_ack.remove( ack )
            else: 
                _reduce = True
            
            flacks = HeaderTCP.get( HeaderTCP.KEYW_FLACKS, responce)
            if not flacks & Protocol_TCP.EFE == 0 : _reduce = True

        _reduce = _reduce or conn.inner_header_tcp.flacks & Protocol_TCP.EFE
        conn.inner_header_tcp.flacks = 0
        if _reduce :
            conn.reduce_frecuency()
        else: 
            conn.increase_frecuency()

            
def recv(conn: Conn, length: int) -> bytes:
    receiver = MySocket( conn.address )
    sender = MySocket( conn.address )

    while True:
        while True:
            w_size, temp_list = conn.recv_all_windows( receiver, length , -1, False, 0)
            if any(temp_list): break

        for msg in temp_list:
            response = Protocol_TCP.map_flack_to_response(msg)
            response.flacks |= conn.inner_header_tcp.flacks 
            response.windows_size = len(temp_list)
            conn.depot_list_msg.append( response.compose() )
            sender.send( conn.depot_list_msg[-1] )
        
        conn.list_msg += temp_list
        conn.inner_header_tcp.flacks = 0
        if len(temp_list) == w_size: break
    
    data = HeaderTCP.get_data_to(conn.list_msg)
    conn.list_msg = []
    return data

def close(conn: Conn):
    header = Protocol_TCP.end_sms(conn.inner_header_tcp)
    header.sequence_number += conn.pivot + 1
    msg = header.compose()
    
    r = conn.send_and_wait_response( 
        msg_to_send = msg, 
        flacks_to_checking = Protocol_TCP.END | Protocol_TCP.ACK,
        error_msg = f"ConnectingError Client not responce for closed"
    )

    return conn
