import asyncio
import socket
from threading import Thread
from typing import Union

class Lamp():
	def __init__(self, Domain: Union[type, str] = None) -> None:
		self.domain = Domain
		self.web_handlers = {}
		self.port = None
		self.ip = None
		self.unix_socket = None
	
	def path(self, path: str,
			status_code: int = 200,
			status: str = 'OK',
			_type: str = 'text/html;'):
		
		def inner(func):
			self.web_handlers[path] = {
				'func': func,
				'status_code': status_code,
				'status': status,
				'type': _type
			}
			return func
		return inner

	async def handle_request(self, client):
		req = client.recv(1024)
		if not req:
			return
		parsed_req = await self.parse(req)
		if parsed_req['path'] not in self.web_handlers:
			return # return a default not found http requests
		head = []
		info = self.web_handlers[parsed_req['path']]

		head.append(f"HTTP/1.1 {info['status_code']} {info['status']}")
		head.append(f"Content-Type: {info['type']} charset=utf-8")
		head.append("Connection: keep-alive")
		head.append("")
		# head.append(f"Content-Type: text/html; charset=utf-8")
		head.append(await info['func']())

		client.send(
			'\r\n'.join(head).encode()
		)
		client.shutdown(socket.SHUT_WR)
		client.close()
	
	async def pare_parms(self, path):
		params = {}
		if '?' not in path:
			return (params, path)
		for parm in (_path := path.split('?', 1))[1].split('&'):
			param = parm.split('=')
			params[param[0]] = param[1]
		return (params, _path[0])

	async def parse(self, req: bytes) -> None:
		parsed_req = {}
		_req = req.splitlines()
		for line in _req:
			if not line:
				parsed_req['body'] = _req[_req.index(line) + 1:]
				break
			if _req.index(line) == 0:
				_line = line.split(b' ')
				parsed_req['requests_type'] = _line[0].decode()
				__p = await self.pare_parms(_line[1].decode())
				parsed_req['params'] = __p[0]
				parsed_req['path'] = __p[1]
				parsed_req['http_vers'] = _line[2].decode()
				continue
			
			_line = line.split(b':')
			parsed_req[_line[0].decode()] = _line[1][1:].decode()
		return parsed_req
	
	async def run(self, _type):
		if type(_type) is tuple:
			await self.run_port(_type)
		else:
			await self.run_unix(_type)
	
	async def run_unix(self, unix_sock: str) -> None:
		...
	
	async def run_port(self, _config: tuple) -> None:
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
			self.ip, self.port = _config
			sock.bind(_config)
			sock.listen(5)
			while True:
				client, _ = sock.accept()
				await self.handle_request(client)
				# loop = asyncio.get_event_loop()
				# loop.run_until_complete(self.handle_request(client))
				# loop.close()


