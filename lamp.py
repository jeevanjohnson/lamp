import asyncio
import socket
import json
from threading import Thread
from typing import Callable, Union
import os

class File():
	def __init__(self, name: str, filename: str, file_bytes: bytes) -> None:
		self.name = name
		self.filename = filename
		self.file_bytes = file_bytes
	
	async def savefile(self, name_overwrite: str = None):
		with open(self.filename if not name_overwrite else name_overwrite, 'wb') as fp:
			fp.write(self.file_bytes)


class Lamp():
	def __init__(self, Domain: Union[type, str] = None) -> None:
		self.domain = Domain
		self.web_handlers = {}
		self.port = None
		self.ip = None
		self.unix_socket = None
		self.buffer_size = 40000000 # image reading?
	
	def path(self, path: str,
			status_code: int = 200,
			status: str = 'OK',
			_type: str = 'html',
			req_type: list = ['GET']) -> Callable:
		
		if _type == 'html':
			_type = 'text/html;'
		elif _type == 'json':
			_type = 'application/json'

		def inner(func):
			self.web_handlers[path] = {
				'func': func,
				'status_code': status_code,
				'status': status,
				'type': _type,
				'req_type': req_type
			}
			return func
		return inner

	async def handle_request(self, client) -> None:
		ctx = {}
		req = client.recv(self.buffer_size)
		if not req:
			return
		parsed_req = await self.parse(req)
		ctx['IP'] = client.getpeername()[0]
		ctx['params'] = parsed_req['params']
		head = []
		if parsed_req['path'] not in self.web_handlers:
			return # return a default not found http requests
		head = []
		info = self.web_handlers[parsed_req['path']]

		if parsed_req['requests_type'] not in info['req_type']:
			return
		
		if parsed_req['requests_type'] == 'POST':
			ctx['file'] = await self.check_for_file(parsed_req['body'])

		head.append(f"HTTP/1.1 {info['status_code']} {info['status']}".encode())
		head.append(f"Content-Type: {info['type']} charset=utf-8".encode())
		head.append("Connection: keep-alive".encode())
		head.append("".encode())
		__func = await info['func'](ctx)
		if info['type'] == 'application/json':
			head.append(
				json.dumps(__func)
			)
		elif info['type'] == 'text/html;':
			head.append(
				__func.encode() if not isinstance(__func, bytes) else __func  
			)
	

		client.send(
			b'\r\n'.join(head)
		)
		client.shutdown(socket.SHUT_WR)
		client.close()
	
	async def check_for_file(self, body):
		file = {}
		for line in body:

			if b'Content-Disposition' in line:
				context = line.split(b':', 1)[1]
				
				for item in context.split(b' '):
					if not item:
						continue
					
					if b'=' in item:
						_item = item.decode().split('=', 1)
						file[_item[0]] = _item[1][1:][:-2 if ';' in _item[1] else -1]
						continue
		
		file['file_bytes'] = b'\n'.join(body[3:][:-1])
		
		return File(
			name = file['name'],
			filename = file['filename'],
			file_bytes = file['file_bytes']
		)

	async def pare_parms(self, path: str) -> tuple:
		params = {}
		if '?' not in path:
			return (params, path)
		for parm in (_path := path.split('?', 1))[1].split('&'):
			param = parm.split('=')
			params[param[0]] = param[1]
		return (params, _path[0])

	async def parse(self, req: bytes) -> dict:
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
	
	def lauch_loop(*args) -> None:
		func = args[1]
		client = args[2]
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		loop.run_until_complete(func(client))
		loop.close()

	async def run(self, _type: Union[str, tuple]) -> None:
		if type(_type) is tuple:
			await self.run_port(_type)
		else:
			await self.run_unix(_type)
	
	async def run_unix(self, unix_sock: str) -> None:
		self.unix_socket = unix_sock
		_unix = unix_sock.split('/')[2][:-5]
		if os.path.exists(unix_sock):
			os.remove(unix_sock)
		
		with socket.socket(socket.AF_UNIX) as sock:
			sock.bind(unix_sock)
			os.chmod(unix_sock, 0o777)
			sock.listen(5)
			print(
				f"Running on http://{_unix}" \
				if not self.domain else f"Running on https://{self.domain}"
				
			)
			while True:
				client, _ = sock.accept()
				Thread(
					target = self.lauch_loop,
					args = (self.handle_request, client)
				).start()

	async def run_port(self, _config: tuple) -> None:
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
			self.ip, self.port = _config
			sock.bind(_config)
			sock.listen(5)
			print(
				f"Running on http://{self.ip}:{self.port}" \
				if not self.domain else f"Running on https://{self.domain}"
				
			)
			while True:
				client, _ = sock.accept()
				Thread(
					target = self.lauch_loop,
					args = (self.handle_request, client)
				).start()