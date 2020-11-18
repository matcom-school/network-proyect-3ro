import time

def parse_address(address):
    host, port = address.split(':')

    if host == '':
        host = 'localhost'

    return host, int(port)

class Singleton(type):
    _instances = None
    def __call__(cls, *args, **kwargs):
        if cls._instances is None:
            cls._instances = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances


def wait_for(func, delta=0.1, timeout=3):
    t = time.time()

    while True:
        tc = time.time()
        if tc > t + timeout:
            raise TimeoutError

        if func():
            break

        time.sleep(delta)