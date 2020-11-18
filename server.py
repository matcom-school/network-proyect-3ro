from trapy import listen,accept,send,recv,close


def chunked_file(file_path, chunk_size):
    with open(file_path, 'rb') as fp:
        while True:
            data = fp.read(chunk_size)
            if len(data) == 0:
                break

            yield data

def handle(conn, file_path, chunk_size):
    for chunk in chunked_file(file_path, chunk_size):
        send(conn, chunk)
    close(conn)


address = ":8000"
_file = "c.txt"
chunk = 40

conn = listen(address)
conn = accept(conn)
handle(conn,_file,chunk)

print("Server Closer !!!!!!!!!!!!!!!!!!!!!!!!")