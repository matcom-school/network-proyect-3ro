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
    def __init__(self, myaddress, inner_header_tcp = None, ws = 1, top_try_conn = 3):
        self.inner_header_tcp = inner_header_tcp if not inner_header_tcp == None else HeaderTCP( source_port= myaddress[1])
        self.address = myaddress
        self.list_ack = []
        self.depot_list_msg = []
        self.list_msg = []
        self.windows_size_cache = ws
        self.windows_size = ws
        self.packet_size = 1
        self.pivot = 0
        self.list_chunk_data = []
        self.try_connection = 0
        self.top_try_conn = top_try_conn
        self.dict_seqnum_responce = {}
        self.end_sys = None

    def demultiplexing( self, response: bytes) -> bool:
        source = HeaderTCP.get( HeaderTCP.KEYW_SOURCE, response)
        destination = HeaderTCP.get( HeaderTCP.KEYW_DESTINATION, response)

        return source == self.inner_header_tcp.destination_post and destination == self.inner_header_tcp.source_port

    def is_good_response(self, response, flacks = 0):
        try:
            result = not HeaderTCP.is_broken( response)
            result = result and self.demultiplexing( response)
            if flacks: 
                result = result and not HeaderTCP.get( HeaderTCP.KEYW_FLACKS, response ) & flacks == 0
        except OverflowError:
            return False
        return result
    
    def reduce_frecuency(self):
        if not self.windows_size == 1:
            self.windows_size = self.windows_size - 1 
    
    def increase_frecuency(self):
        if self.windows_size < len(self.list_msg):
            self.windows_size = self.windows_size + 1
        else: self.windows_size = len(self.list_msg)
    
    def send_and_wait_response(self, msg_to_send, flacks_to_checking , error_msg, do_answer = False):
        sender = MySocket( self.address ) 
        receiver = MySocket( self.address )
        for _ in range(5):
            sender.send( msg_to_send)
            try:
                #wait_for(receiver.recv( blocking= False))
                timeout, resp = receiver.recv_all_windows(0,1)
                if timeout: raise TimeoutError
                receiver.data = resp[0]
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
                
    def compose_all_packet(self):
        for chunck_data in self.list_chunk_data:
            packet = Protocol_TCP.normal_sms(self.inner_header_tcp)
            packet.sequence_number += self.pivot + 1
            packet.__dict__["data"] = chunck_data
            self.list_ack.append(packet.sequence_number)
            self.pivot += 1
            self.list_msg.append(packet)
            self.depot_list_msg.append(packet)
        
    def find_packet(self, _list: list, seq_num):
        for packet in _list:
           if seq_num == HeaderTCP.get(HeaderTCP.KEYW_SEQUENCE, packet):
               return packet
    def reconnecting(self, sender ):
        reconn = HeaderTCP(
            source_port= self.inner_header_tcp.source_port,
            destination_post= self.inner_header_tcp.destination_post,
            sequence_number= self.inner_header_tcp.ack_number,
            ack_number= self.inner_header_tcp.sequence_number + 1,
            flacks= Protocol_TCP.END | Protocol_TCP.SYS
        )
        responce = reconn.compose()
        sender.send( responce )

    def try_if_cant_close(self):
        if self.try_connection == self.top_try_conn:
            raise ConnException("Server is down")
        
        self.try_connection += 1
        logger.info(f'Trying number {self.try_connection} to reconnecting ')

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
    conn = Conn( conn.address, header_resp, top_try_conn= 20)
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
    conn.end_sys = Protocol_TCP.map_flack_to_response( response ).compose()

    print("Connected !!!!!!!!")
    header_resp,_ = HeaderTCP.descompose(response)
    conn.inner_header_tcp.ack_number = header_resp.sequence_number
    return conn


def send(conn: Conn, data: bytes) -> int:
    sockett = MySocket( conn.address )
    conn.fraction_data(data)
    conn.compose_all_packet()
    if conn.windows_size == 0: conn.windows_size = 1
    _len = len(conn.list_chunk_data)
    conn.list_chunk_data = []
    while any(conn.list_ack) and any(conn.list_msg):

        #print(conn.windows_size)
        for i in range( conn.windows_size ):
            msg = conn.list_msg[i]
            msg.windows_size = conn.windows_size
            msg.ack_number = _len
            msg = msg.compose( msg.data )
            #print(HeaderTCP.to_str(msg))
            sockett.send(msg)
    
        timeout, recv_list = sockett.recv_all_windows( 0, conn.windows_size)
        about = True
        for msg in recv_list:
            if conn.is_good_response( msg, Protocol_TCP.ACK ):
                ack = HeaderTCP.get( HeaderTCP.KEYW_ACK, msg )
                flack = HeaderTCP.get( HeaderTCP.KEYW_FLACKS, msg )
                try:
                    i = conn.list_ack.index( ack )
                    conn.list_ack.remove( conn.list_ack[i] )
                    conn.list_msg.remove( conn.list_msg[i] )
                    conn.try_connection = 0
                    about = False
                    if not flack & Protocol_TCP.EFE == 0 : timeout = True 
                except ValueError:
                    timeout = True
            else:
                timeout = True
        
        if about: conn.try_if_cant_close()
        if timeout : conn.reduce_frecuency()
        else: conn.increase_frecuency()

            
def recv(conn: Conn, length: int) -> bytes:
    sockett = MySocket( conn.address )
    data_recv = []
    _len = 0
    flack = 0

    while True:
        while True:
            timeout, recv_list = sockett.recv_all_windows( conn.packet_size, -1)
            if any(recv_list):
                conn.try_connection = 0
                break
            if conn.end_sys:
                sockett.send( conn.end_sys )
            conn.try_if_cant_close()    
        
        conn.end_sys = None

        temp = []
        for msg in recv_list:
            if conn.is_good_response(msg):
               temp.append(msg) 
        
        if any(temp):
            flack = HeaderTCP.get( HeaderTCP.KEYW_FLACKS, temp[0])
            if flack == Protocol_TCP.SYS | Protocol_TCP.ACK:
                conn.reconnecting( sockett )
                continue
            elif not _len : 
                _len = HeaderTCP.get( HeaderTCP.KEYW_ACK, temp[0])
        
        recv_list = temp
        ws = len(recv_list)
        for msg in recv_list:
            seqnum = HeaderTCP.get( HeaderTCP.KEYW_SEQUENCE, msg )
            try:
                header_resp = conn.dict_seqnum_responce[ seqnum ]
            except KeyError:
                data_recv.append( msg )
                header_resp = Protocol_TCP.map_flack_to_response( msg )
                conn.dict_seqnum_responce[ seqnum ] = header_resp
                if not ws == header_resp.windows_size: 
                    header_resp.flacks |= Protocol_TCP.EFE
              
            header_resp.windows_size = ws
            responce = header_resp.compose()
            header_resp.flacks |= Protocol_TCP.EFE
            sockett.send( responce )
        
        if _len == len(conn.dict_seqnum_responce) and _len: break
    
    conn.dict_seqnum_responce = {}
    data = HeaderTCP.get_data_to(data_recv)    
    return data

def close(conn: Conn):
    header = Protocol_TCP.end_sms(conn.inner_header_tcp)
    header.sequence_number += conn.pivot + 1
    header.ack_number = 1
    msg = header.compose()
    
    r = conn.send_and_wait_response( 
        msg_to_send = msg, 
        flacks_to_checking = Protocol_TCP.END | Protocol_TCP.ACK,
        error_msg = f"ConnectingError Client not responce for closed"
    )

    print("Closed connection with", conn.inner_header_tcp.destination_post)
    return conn
