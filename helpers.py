
import os

def render_template(path_to_html):
	_p = path_to_html.split('/')
	del _p[len(_p) - 1]
	with open(path_to_html, 'r') as fp:
		_fp = fp.read()
	_index = 0
	for line in (__fp := _fp.splitlines()):
		if '<link' not in line:
			_index += 1
			continue
		parsed_line = line[6:][:-1]
		_types = {}
		for x in parsed_line.split(' '):
			x = x.split('=')
			x[1] = x[1][1:][:-1]
			_types.update({k: v for k,v in [x]})
		
		if 'rel' in _types:
			if _types['rel'] == 'stylesheet':
				with open(f'{"/".join(_p)}/{_types["href"]}', 'r') as f:
					__fp[_index] = "<style>" + f.read() + "</style>"
		_index += 1
	return '\n'.join(__fp).encode()