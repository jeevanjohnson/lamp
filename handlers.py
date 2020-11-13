import asyncio
import config
import socket
import time

class Handlers:
	def __init__(self, client, context) -> None:
		self.client = client
		self.context = context
		self.request_type = None
		self.path = None
		self.filename = None
		self.file_bytes = None
		self.params = {}
		self.data = {}
		self.pages = {
		'/': self.homepage, 
		'/get_file?': self.get_file,
		'/post': self.get_post
		}

	def parse(self, context):
		if not context:
			return
		try:
			_context = context.decode().replace('\r', '')
		except:
			if (request_type := context.split(b' ')[0]) == b'POST':
				self.request_type = request_type.decode()
				self.context = context.replace(b'\r', b'').split(b'\n')
				self.get_file_info()
			return
		_context = _context.split('\n')
		self.context = _context
		context = _context[0].split(' ')
		self.request_type = context[0]
		if self.request_type == "POST":
			self.get_file_info()
		if '?' in context[1]:
			self.path = context[1].split('?')[0] + '?'
			tempname = ''
			_params = ' '.join(' '.join(''.join(context[1].split('?')[1]).split('=')).split('&')).split(' ')
			for param in _params:
				if _params.index(param) + 1 & 1: # odd number check
					self.params[param] = None
					tempname = param
				else:
					self.params[tempname] = param
		else:
			self.path = context[1]
			return
	
	def get_file_info(self):
		for line in self.context:
			if 'Content-Disposition:' in (line := line.decode()):
				_index = self.context.index(line.encode())
				line = line.replace('Content-Disposition:','').replace('form-data;','')
				tempname = ''
				line = ' '.join(''.join(line.split(';')).split('=')).split(' ')[2:]
				for data in line:
					if line.index(data) + 1 & 1:
						self.data[data] = None
						tempname = data
					else:
						self.data[tempname] = data.replace('"','')
				break
		_file = self.context[_index + 1:]
		with open(self.data['filename'].replace('crocs','crocs2'), 'wb') as f:
			self.file_bytes = b' '.join(_file) 
			f.write(self.file_bytes) # this doesn't work :C


	def render_variables(self, html_file):
		_html_file = html_file.replace('%]','[%').split('[%')
		for line in _html_file:
			_index = _html_file.index(line)
			if '<' in line or '>' in line:
				continue
			if 'import' in line:
				line = line.replace('import','').replace(' ', '').replace('\n','')
				_html_file[_index] = f'[% import {line} %]'
				try:
					with open(f"{config.PATH_TO_CSS_FOLDER}/{line}") as e:
						style = e.read()
					_html_file[_index] = _html_file[_index].replace(f"[% import {line} %]".format(line=line), (man := "<style>\n" + style + "</style>"))
					html_file = ''.join(_html_file)
				except Exception as l:
					print(str(l))
		return html_file

	def render_template(self, path_to_html_file):
		with open(path_to_html_file, 'r') as f:
			html_file = f.read()
		if '[%' in html_file and '%]' in html_file:
			html_file = self.render_variables(html_file)
		headers = "HTTP/1.1 200 OK\r\n"
		headers += "Content-Type: text/html; charset=utf-8\r\n"
		headers += "Connection: keep-alive\r\n"
		headers += "\r\n"
		headers += f'{html_file}\r\n\r\n'
		return headers

	def render_json(self, json):
		headers = "HTTP/1.1 200 OK\r\n"
		headers += "Content-Type: application/json\r\n"
		headers += "Connection: keep-alive\r\n"
		headers += "\r\n"
		headers += f'{json}\r\n\r\n'
		return headers
	
	def homepage(self):
		curr_time = int(time.time() * 1000)
		headers = self.render_template(config.HOMEPAGE_HTMLFILE_PATH)
		self.client.send((message := headers.encode()))
		this_time = int(time.time() * 1000)
		mili = this_time - curr_time
		print(f'Sent the following headers:\n{message.decode()}\nTook {mili} ms!')
		self.client.shutdown(socket.SHUT_WR)
		self.client.close()

	def get_post(self):
		curr_time = int(time.time() * 1000)
		headers = self.render_template(config.SUCCESS_HTMLFILE_PATH)
		self.client.send((message := headers.encode()))
		this_time = int(time.time() * 1000)
		mili = this_time - curr_time
		print(f'Sent the following headers:\n{message.decode()}\nTook {mili} ms!')
		self.client.shutdown(socket.SHUT_WR)
		self.client.close()

	def not_found(self):
		curr_time = int(time.time() * 1000)
		headers = self.render_template(config.NOT_FOUND_HTMLFILE_PATH)
		self.client.send((message := headers.encode()))
		this_time = int(time.time() * 1000)
		mili = this_time - curr_time
		print(f'Sent the following headers:\n{message.decode()}\nTook {mili} ms!')
		self.client.shutdown(socket.SHUT_WR)
		self.client.close()

	def get_file(self):
		curr_time = int(time.time() * 1000)
		headers = self.render_json(self.params)
		self.client.send((message := headers.encode()))
		this_time = int(time.time() * 1000)
		mili = this_time - curr_time
		print(f'Sent the following headers:\n{message.decode()}\nTook {mili} ms!')
		self.client.shutdown(socket.SHUT_WR)
		self.client.close()

	async def check(self):
		self.parse(self.context)
		if self.context:
			try:
				return self.pages.get(self.path)()
			except:
				return self.not_found()

