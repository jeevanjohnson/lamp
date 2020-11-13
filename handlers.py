import asyncio
import config
import socket

class Handlers:
	def __init__(self, client, context) -> None:
		self.client = client
		self.context = context
		self.request_type = None
		self.path = None
		self.params = {}

	def parse(self, context):
		if not context:
			return
		_context = context.decode().replace('\r', '')
		_context = _context.split('\n')
		self.context = _context
		context = _context[0].split(' ')
		self.request_type = context[0]
		if '?' in context[1]:
			self.path = context[1].split('?')[0] + '?'
			tempname = ''
			_params = ''.join(context[1].split('?')[1]).split('=')
			for param in _params:
				if _params.index(param) + 1 & 1: # odd number check
					self.params[param] = None
					tempname = param
				else:
					self.params[tempname] = param
		else:
			self.path = context[1]
			return

	def render_template(self, path_to_html_file):
		with open(path_to_html_file, 'r') as f:
			html_file = f.read()
		headers = "HTTP/1.1 200 OK\r\n"
		headers += "Content-Type: text/html; charset=utf-8\r\n"
		headers += "\r\n"
		headers += f'{html_file}\r\n\r\n'
		return headers

	def render_json(self, _json):
		headers = "HTTP/1.1 200 OK\r\n"
		headers += "Content-Type: text/html; charset=utf-8\r\n"
		headers += "\r\n"
		headers += f'{_json}\r\n\r\n'
		return headers
	
	def homepage(self):
		headers = self.render_template(config.HOMEPAGE_HTMLFILE_PATH)
		self.client.send((message := headers.encode()))
		print(f'Sent the following headers: {message.decode()}')
		self.client.shutdown(socket.SHUT_WR)
		self.client.close()

	def not_found(self):
		headers = self.render_template(config.NOT_FOUND_HTMLFILE_PATH)
		self.client.send((message := headers.encode()))
		print(f'Sent the following headers: {message.decode()}')
		self.client.shutdown(socket.SHUT_WR)
		self.client.close()

	def get_file(self):
		headers = self.render_json(self.params)
		self.client.send((message := headers.encode()))
		print(f'Sent the following headers: {message.decode()}')
		self.client.shutdown(socket.SHUT_WR)
		self.client.close()

	def check(self):
		self.parse(self.context)
		if self.context:
			try:
				return {
					'/': self.homepage,
					'/get_file?': self.get_file
				}.get(self.path)()
			except:
				return self.not_found()

