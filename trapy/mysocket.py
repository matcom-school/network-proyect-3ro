import socket
import subprocess
import os
from .utils import wait_for
from .header_tcp import HeaderTCP
import time

from random import randint
def tester( bites ):
    return bites
    #i = randint(0,100)
    #if i % 3 == 0: return b"$aniel" + bites
    #else: return bites

class MySocket:
    def __init__( self, sender_directions = None, receiver_directions = None):
        self.data = ""
        self.sender_directions = sender_directions
        self.receiver_directions = receiver_directions
        self.s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)

    def recv( self, datasize : int = 0, blocking: bool = True):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        self.s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        self.s.bind( self.receiver_directions )

        size = HeaderTCP.size()
        if blocking: 
            result, direct = self.s.recvfrom(20 + size + datasize)
            if self.sender_directions is None: self.sender_directions = direct
            self.s.close()
            return tester(result[20:])

        self.s.setblocking(0)
        def a ():
            try:
                self.data = tester( self.s.recvfrom(20 + size + datasize)[0][20:] )
                return True
            except BlockingIOError:
                return False
        return a

    def recv_all_windows(self, lengh, window_size, timeout = 3, ws = True):
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        s.bind( self.receiver_directions )
        s.setblocking(0)
        size = HeaderTCP.size()
    
        t = time.time()
        result = [] 
        while True:
            tc = time.time()
            if ws and window_size == -1 and any(result):
                try:
                    window_size = HeaderTCP.get( HeaderTCP.KEYW_SIZE_W, result[0] )
                except OverflowError:
                    pass
            if window_size == len(result):
                return False, result
            if tc > t + timeout :
                return True, result
            try:
                result.append( tester( s.recvfrom(20 + size + lengh)[0][20:] )) 
            except BlockingIOError:
                pass
        s.close()
        

    def send(self, packet):
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        s.sendto(packet, self.sender_directions)
        s.close()

    def close(self):
        self.s.close()

    def send_and_wait_to_response(self, msg, timer = 3, amount_try = 5, error_msg = "" ):
        count = 0
        while True:
            self.send( msg)
            try:
                wait_for(self.recv( blocking= False) , timeout= timer)
                break
            except TimeoutError:
                count += 1
                if count == amount_try:
                    raise TimeoutError(error_msg)
        
        return self.data

if __name__ == "__main__":
    s = MySocket(("localhost",0))
    wait_for(s.recv( blocking= False))

    print(s.data)