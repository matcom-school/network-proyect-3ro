from trapy import dial,recv

address = ":8000"


conn = dial(address)
data = []
while True:
    chunk = recv(conn, 1024)
    print(chunk)
    if len(chunk) == 0:
        break
    data.append(chunk)

data = b''.join(data)
print(data)

print("Client Closer !!!!!!!!!!!!!!!!!!!!!!!!")