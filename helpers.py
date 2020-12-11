import re
import os

def remove_extra_space(string: str) -> str:
	def func(string: str) -> str:
		_index = 0
		for char in string:

			if not char or char == ' ':
				_index += 1
			else:
				break
		return string[_index:]

	return func(func(string)[::-1])[::-1]

def render_template(path_to_html: str, **kwargs) -> bytes:
	_p = path_to_html.split('/')
	_p = _p[:-1]
	with open(path_to_html, 'r') as fp:
		_fp = fp.read()
	_index = 0
	for line in (__fp := _fp.splitlines()):

		var = re.search(r'//(.+?)//', line)
		if kwargs and var:
			for key in kwargs:
				for _var in var.groups():
					if (__var := remove_extra_space(_var)) == key:
						__fp[_index] = line.replace(_var, __var)
						__fp[_index] = line.replace(f'//{_var}//', str(kwargs[key]))	

		if '<link' not in line:
			_index += 1
			continue
		parsed_line = line[6:][:-1]
		_types = {}
		for x in parsed_line.split(' '):
			x = x.split('=')
			x[1] = x[1][1:][:-1]
			_types[x[0]] = x[1]
		
		if 'rel' in _types:
			if _types['rel'] == 'stylesheet':
				with open(f'{"/".join(_p)}/{_types["href"]}', 'r') as f:
					__fp[_index] = "<style>" + f.read() + "</style>"
		_index += 1
	return '\n'.join(__fp).encode()