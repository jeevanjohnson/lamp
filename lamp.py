import socket
import os
from typing import Callable, Union
import asyncio
from threading import Thread

class Route():
	def __init__(self, func: Callable, methods: list) -> None:
		self.func = func
		self.methods = methods

class CTX():
	def __init__(self) -> None:
		...

class Lamp():
	def __init__(self, domain: Union[str, type] = None) -> None:
		self.routes = {}
		self.ip = None
		self.port = None
		self.unix_sock = None
		self.header_override = None
		self.domain = domain
	
	def route(self, path: str, methods: list = ['GET']):
		def inner(func):
			self.routes[path] = Route(func, methods)
			return func
		return inner

	def check_for_file(self, parsed_data: dict) -> tuple:
		if not parsed_data['body']:
			return parsed_data, False
		line = parsed_data['body'][1].decode().split(':', 1)[1].split()
		Content_Disposition = {}
		for item in line:
			if '=' not in item:
				continue
			item = item.split('=', 1)
			Content_Disposition[item[0]] = item[1][1:][:-2 if item[1][-1] == ';' else -1]
		
		parsed_data['Content_Disposition'] = Content_Disposition
		parsed_data['body'] = parsed_data['body'][3:][:-1]
		
		if Content_Disposition['name'] == 'file':
			return parsed_data, True
		else:
			return parsed_data, False
	
	def handle_request(self, client, req: dict) -> None:
		if self.header_override:
			head = self.routes[req['route']].func()
			client.sendall(head)
			client.shutdown(socket.SHUT_WR)
			client.close()
			return
			
	
	def _parse(self, data: bytes) -> dict:
		_data = data.splitlines()
		parsed_data = {}
		_index = 0
		for line in _data:
			line = line.decode()
			if not line:
				break
			if not _index:
				line = line.split()
				parsed_data['method'] = line[0]
				parsed_data['route'] = line[1]
				parsed_data['http_vers'] = line[2]
				_index += 1
				continue

			line = line.split(':')
			parsed_data[line[0]] = line[1][1:]
		
			_index += 1
			
		parsed_data['body'] = _data[_index + 1:]
		
		return parsed_data

	def parse_request(self, client) -> None:
		data = client.recv(1024)
		parsed_data = self._parse(data)
		parsed_data = self.check_for_file(parsed_data)
		if parsed_data[1]:
			parsed_data = parsed_data[0]
			for line in client.recv(1000000).splitlines():
				parsed_data['body'].append(line)
			parsed_data['body'] = parsed_data['body'][:-1]
		
		if type(parsed_data) is tuple:
			parsed_data = parsed_data[0]

		if self.domain:
			if parsed_data['Host'] == self.domain:
				self.handle_request(client, parsed_data)
		else:
			self.handle_request(client, parsed_data)

	def run(self, _socket: Union[tuple, str] = ("127.0.0.1", 5000), 
			header_override: bool = False) -> None:
		if header_override:
			self.header_override = header_override
		loop = asyncio.get_event_loop()
		if type(_socket) is tuple:
			__socket = socket.AF_INET
			_bind = self.ip, self.port = _socket
		else:
			__socket = socket.AF_UNIX
			_bind = self.unix_sock = _socket
			if os.path.exists(_socket):
				os.remove(_socket)

		with socket.socket(__socket) as sock:
			sock.bind(_bind)
			if isinstance(_bind, str):
				os.chmod(_bind, 0o777)
			sock.listen(5)

			while True:
				client, _ = sock.accept()
				Thread(target = self.parse_request, args = (client,)).start()