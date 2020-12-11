import socket
import os
from typing import Callable, Union
import asyncio
from threading import Thread
import json

HTTP_STATUS_CODES = { # source of these can be found on https://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
	100: 'Continue',
	101: 'Switching Protocols',
	200: 'OK',
	201: 'Created',
	202: 'Accepted',
	203: 'Non-Authoritative Information',
	204: 'No Content',
	205: 'Reset Content',
	206: 'Partial Content',
	300: 'Multiple Choices',
	301: 'Moved Permanently',
	302: 'Found',
	303: 'See Other',
	304: 'Not Modified',
	305: 'Use Proxy',
	306: '(Unused)', # ehhh
	307: 'Temporary Redirect',
	400: 'Bad Request',
	401: 'Unauthorized',
	402: 'Payment Required', # soon?
	403: 'Forbidden',
	404: 'Not Found',
	405: 'Method Not Allowed',
	406: 'Not Acceptable',
	407: 'Proxy Authentication Required',
	408: 'Request Timeout',
	409: 'Conflict',
	410: 'Gone',
	411: 'Length Required',
	412: 'Precondition Failed',
	413: 'Request Entity Too Large',
	414: 'Request-URI Too Long',
	415: 'Unsupported Media Type',
	416: 'Requested Range Not Satisfiable',
	417: 'Expectation Failed',
	500: 'Internal Server Error',
	501: 'Not Implemented',
	502: 'Bad Gateway',
	503: 'Service Unavailable',
	504: 'Gateway Timeout',
	505: 'HTTP Version Not Supported'
}

Content_Type = { # more coming soon
	'HTML': 'text/html;',
	'JSON': 'application/json',
	'IMAGE_JPEG': 'image/jpeg'
}

Default_headers = {
	404: f'HTTP/1.1 404 Not Found\r\nContent-Type: application/json charset=utf-8\r\nConnection: keep-alive\r\n\r\n{json.dumps({404: "Not Found"})}'.encode(),
	405: f'HTTP/1.1 405 Method Not Allowed\r\nContent-Type: application/json charset=utf-8\r\nConnection: keep-alive\r\n\r\n{json.dumps({405: "Method Not Allowed"})}'.encode()
}

class TemplatePathNotFound(Exception):
	pass

class Error():
	def __init__(self, func: Callable, 
					status_code: int = 200 ,
					content_type: str = 'HTML') -> None:
		
		self.func = func
		self.status_code = status_code
		self.content_type = content_type
		self.headers = b''
	
	def set_headers(self, content: Union[object, bool] = None) -> bytes:
		self.headers += f'HTTP/1.1 {self.status_code} {HTTP_STATUS_CODES.get(self.status_code)}\r\n'.encode()
		self.headers += f'Content-Type: {Content_Type.get(self.content_type)} charset=utf-8\r\n'.encode()
		self.headers += b'Connection: keep-alive\r\n'
		self.headers += b'\r\n'
		if content:
			self.headers += self.func(content)
		else:
			self.headers += self.func()
		
		return self.headers

class Route():
	def __init__(self, func: Callable, 
					methods: list = ['GET'],
					status_code: int = 200 ,
					content_type: str = 'HTML') -> None:
		
		self.func = func
		self.status_code = status_code
		self.methods = methods
		self.content_type = content_type
		self.headers = b''
	
	def set_headers(self, content: Union[object, bool] = None) -> None:
		self.headers = b''
		self.headers += f'HTTP/1.1 {self.status_code} {HTTP_STATUS_CODES.get(self.status_code)}\r\n'.encode()
		self.headers += f'Content-Type: {Content_Type.get(self.content_type)} charset=utf-8\r\n'.encode()
		self.headers += b'Connection: keep-alive\r\n'

		if self.content_type == 'IMAGE_JPEG':
			self.headers += f'Accept-Ranges: bytes\r\n\r\n'.encode()

		self.headers += b'\r\n'

		if content:
			self.headers += self.func(content)
		else:
			self.headers += self.func()

class Content():
	def __init__(self, **kwargs) -> None:
		if 'req' in kwargs:
			self.header = kwargs['req']
		

	def save_file(self):
		...


class Lamp():
	def __init__(self, domain: Union[str, type] = None) -> None:
		self.routes = {}
		self._error_handler = {}
		self.ip = None
		self.port = None
		self.unix_sock = None
		self.header_override = None
		self.template_path = None
		self.domain = domain
	
	def template_path(self, path: str) -> None:
		if not os.path.exists(path):
			raise TemplatePathNotFound(f"{path} couldn't be found")
		
		self.template_path = path

	def error_handler(self, status_code: int = 200,
					  content_type: str = 'HTML') -> Callable:
		def inner(func):
			self._error_handler[status_code] = Error(func, status_code, content_type)
			return func
		return inner	
	
	def route(self, path: str, methods: list = ['GET'], 
			  status_code: int = 200, content_type: str = 'HTML') -> Callable:
		def inner(func):
			self.routes[path] = Route(func, methods, status_code, content_type)
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
		if len(req) < 2:
			return
		ctx = Content(req = req)
		if self.header_override:
			head = self.routes[req['route']].func(ctx)
			client.sendall(head)
			client.shutdown(socket.SHUT_WR)
			client.close()
			return
		
		if req['route'] not in self.routes:
			if 404 not in self._error_handler:
				head = Default_headers.get(404)
			else:
				head = self._error_handler[404].set_headers(ctx)
			client.sendall(head)
			client.shutdown(socket.SHUT_WR)
			client.close()
			return
		
		if req['method'] not in (_route := self.routes[req['route']]).methods:
			if 405 not in self._error_handler:
				head = Default_headers.get(405)
			else:
				head = self._error_handler[405].set_headers(ctx)
			client.sendall(head)
			client.shutdown(socket.SHUT_WR)
			client.close()
			return
		
		_route.set_headers(ctx)
		client.sendall(_route.headers)
		client.shutdown(socket.SHUT_WR)
		client.close()
		return
	
	def parse_params(self, route: str) -> tuple:
		params = {}
		if not '?' in route:
			return params, route
		
		_route = route.split('?', 1)[1].split('&')

		for param in _route:
			param = param.split('=', 1)
			params[param[0]] = param[1]
		
		return params, route.split('?', 1)[0]
	
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
				parsed_data['params'], parsed_data['route'] = self.parse_params(line[1])
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