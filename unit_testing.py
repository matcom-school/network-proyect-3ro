from trapy.header_tcp import HeaderTCP

def accept(a,b, string):
    if not a == b:
        raise Exception
    print(string)
header = HeaderTCP(
    source_port= 8000,
    destination_post= 9000,
    sequence_number= 12345,
    ack_number= 54321,
    flacks= 3,
    windows_size= 5
    )

accept(
    a= str(header.__dict__),
    b= "{'source_port': 8000, 'destination_post': 9000, 'sequence_number': 12345, 'ack_number': 54321, 'flacks': 3, 'windows_size': 5}",
    string= "Create ---------------------------- OK"
)
msg = header.compose(data=b"Daniel")
accept(
    a= msg,
    b= b'\x1f@#(\x00\x0009\x00\x00\xd41\x05\x03\x00nDaniel',
    string= "Compose ---------------------------- OK"
)

accept(
    a= HeaderTCP.is_broken(msg),
    b= False,
    string= "---------------------------- "
)

broke = b"\x00" + msg
accept(
    a= HeaderTCP.is_broken(broke),
    b= True,
    string= "Is Broke ---------------------------- OK"
)

h,d = HeaderTCP.descompose(broke)
accept(
    a= str(h.__dict__),
    b= "{'source_port': 31, 'destination_post': 16419, 'sequence_number': 671088688, 'ack_number': 956301524, 'flacks': 5, 'windows_size': 49}",
    string= "---------------------------- "
)
accept(
    a= d,
    b= b"nDaniel",
    string= "Descompose ---------------------------- OK "
)

accept(
    a= HeaderTCP.get_data_to([msg, broke]),
    b= b"DanielnDaniel",
    string= "Get Data To---------------------------- OK "
)

from trapy.protocol_tcp import Protocol_TCP

header = Protocol_TCP.sys_wich([8000,9000])

print("strprint ------->",Protocol_TCP.map_flack_to_response(header).__dict__,"\n")