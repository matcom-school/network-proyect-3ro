import binascii
from random import randint


class HeaderTCP:
	KEYW_SOURCE = "source_port"
	KEYW_DESTINATION = "destination_post"
	KEYW_SEQUENCE = "sequence_number"
	KEYW_ACK = "ack_number"
	KEYW_FLACKS = "flacks"
	KEYW_SIZE_W = "windows_size"
	
	def __init__(self, source_port = 0, destination_post = 0, sequence_number = 0, ack_number = 0, flacks = 0, windows_size = 0):
		self.source_port = source_port
		self.destination_post = destination_post
		self.sequence_number = sequence_number
		self.ack_number = ack_number
		self.flacks = flacks
		self.windows_size = windows_size
	
	def compose(self, data = b'', header_tcp_dict = None ) -> bytes:
		_dict = self.__dict__.copy()
		
		if not header_tcp_dict == None:
			for key,value in header_tcp_dict:
				_dict[key] = value
		
		return HeaderTCP.compose_wish_dict( _dict, data)
	
	@staticmethod
	def get_data_to( _list):
		_list.sort(key = lambda x : HeaderTCP.get( HeaderTCP.KEYW_SEQUENCE, x) )
		data = b''
		for msg in _list:
			_, mini_data = HeaderTCP.descompose( msg )
			data += mini_data
		
		return data
		

	@staticmethod
	def is_broken( msg : bytes ) -> bool:
		_len = len(HeaderTCP.__void_tcp_header())
		if len(msg) < _len + 2 : return False

		check_sum = int.from_bytes(msg[_len: _len + 2],'big')
		return not check_sum == ( HeaderTCP.compute_cheksum( msg[:_len], msg[_len+2:] ) % 255 )

	@staticmethod
	def descompose(msg : bytes):
		result = HeaderTCP()
		_len = len(HeaderTCP.__void_tcp_header())
		_map = HeaderTCP.__map_hearder()
		for section in HeaderTCP.__section_list():
			a,b = _map[section]
			result.__dict__[section] = int.from_bytes(msg[a:b],'big')
		
		return result, msg[_len + 2:]

	@staticmethod
	def compose_wish_dict(_dict,data) -> bytes:
		tcp_header = list(HeaderTCP.__void_tcp_header())
		_map = HeaderTCP.__map_hearder()
		for section in HeaderTCP.__section_list():
			a,b = _map[section]
			tcp_header[a:b] = list(_dict[section].to_bytes(b-a,'big'))

		tcp_header = bytes(tcp_header)
		return tcp_header + (HeaderTCP.compute_cheksum(tcp_header,data) % 255).to_bytes(2,'big') + data

	@staticmethod
	def compute_cheksum( header : bytes, data : bytes):
		crc = binascii.crc32(header)
		result = binascii.crc32(data,crc)
		return result

	@staticmethod
	def get(section ,msg : bytes) -> int :
		_map = HeaderTCP.__map_hearder()
		a, b = _map[ section ]
		return int.from_bytes(msg[a:b],'big')

	@staticmethod
	def to_str(msg : bytes) -> str:
		result = ''
		_len = len(HeaderTCP.__void_tcp_header())
		_map = HeaderTCP.__map_hearder()
		for section in HeaderTCP.__section_list():
			a,b = _map[section]
			result += f"{int.from_bytes(msg[a:b],'big')} | "
		
		result += f"{int.from_bytes(msg[_len : _len + 2],'big')} | "
		return result
	@staticmethod
	def size():
		header = HeaderTCP.__void_tcp_header()
		return len(header) + 2

	@staticmethod
	def __section_list():
		return [ HeaderTCP.KEYW_SOURCE, HeaderTCP.KEYW_DESTINATION, HeaderTCP.KEYW_SEQUENCE, HeaderTCP.KEYW_ACK, HeaderTCP.KEYW_FLACKS, HeaderTCP.KEYW_SIZE_W]

	@staticmethod
	def __map_hearder():
		return {
			HeaderTCP.KEYW_SOURCE : (0,2),
			HeaderTCP.KEYW_DESTINATION : (2,4),
			HeaderTCP.KEYW_SEQUENCE : (4,8),
			HeaderTCP.KEYW_ACK : (8,12),
			HeaderTCP.KEYW_SIZE_W: (12,13),
			HeaderTCP.KEYW_FLACKS: (13,14),
		}

	__flack_func_response = {}

	@staticmethod
	def __void_tcp_header() -> bytes:
		tcp_header  = b'\x00\x00\x00\x00' # Source Port | Destination Port
		tcp_header += b'\x00\x00\x00\x00' # Sequence Number
		tcp_header += b'\x00\x00\x00\x00' # Acknowledgement Number
		tcp_header += b'\x00\x00' # Data Offset, Reserved, Flags | Window Size
		#tcp_header += b'\x00\x00\x00\x00' # Checksum | Urgent Pointer
		return tcp_header


if __name__ == "__main__":
	tcp = HeaderTCP(8000,12)
	a = tcp.compose(
		header_tcp_dict= {
			HeaderTCP.KEYW_ACK : 107,
			HeaderTCP.KEYW_SIZE_W : 3,
			HeaderTCP.KEYW_FLACKS : 3
		},
		data= b'Daniel'
	)
	print(a)
	print(HeaderTCP.to_str(a))