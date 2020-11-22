from random import randint
from .utils import Singleton

class PortManager():
    def __init__(self, _file, bits = 16):
        try:
            f = open( _file, "x" )
            f.close()
        except FileExistsError:
            pass
        
        self.file = _file
        self.port_on = self.read()
        top = 1
        for _ in range(bits - 1):
            top = top * 2
            top += 1
        self.top = top
    
    def get_free_port(self) -> int:
        while True:
            r = randint(0,self.top)        
            if not r in self.port_on: 
                self.port_on.append(r)
                self.write()
                return r

    def free(self,port):
        self.port_on.remove(port)
        self.write()
    
    def on(self, port):
        if port in self.port_on:
            raise ConnectionError
        self.port_on.append(port)
        self.write()

    def write(self):
        f = open( self.file, "w")
        f.write(str(self.port_on))
        f.close

    def read(self):
        f = open(self.file,"r")
        t = f.readline()
        t = t[1:-1]
        t = t.split(",")
        result = []
        for port in t:
            try:
                result.append( int(port) )
            except ValueError:
                pass
        f.close()
        return result

class ClientPortManager(PortManager, metaclass=Singleton):
    def __init__(self,bits = 16):
        super().__init__("client_port_data_base.txt",bits)

class ServerPortManager(PortManager,metaclass=Singleton):
    def __init__(self,bits = 16):
        super().__init__("server_port_data_base.txt",bits)

if __name__ == "__main__":
    print(ClientPortManager(3).top)
    print(ClientPortManager(300000).top)
    print(ServerPortManager(5).top)
    print(ServerPortManager(30000).top)
    s = ServerPortManager()
    print(s.get_free_port())
    print(s.get_free_port())
    print(s.get_free_port())
    d = s.get_free_port()
    print(d)
    print(s.port_on)
    s.free(d)
    print(s.port_on)
