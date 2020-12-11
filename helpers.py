import re
import os
import json

def jsonify(_json: dict) -> bytes:
	return json.dumps(_json).encode()

def render_template(path_to_html: str, **kwargs) -> bytes:
	template_path = '/'.join(path_to_html.split('/')[:-1])
	
	with open(path_to_html, 'r') as fp:
		html_file = fp.read().splitlines()
	
	_index = 0
	for line in html_file:
		if kwargs:
			variable = re.search(r'//(.+?)//', line)
			if variable:
				for key in kwargs:
					for var in variable.groups():
						if (var_stripped := var.strip()) == key:
							html_file[_index] = line = line.replace(var, var_stripped)
							html_file[_index] = line = line.replace(f'//{var_stripped}//', str(kwargs[key]))
		
		if '<link' in line:
			_index += 1
			
			parsed_line = line[6:][:-1]
			_types = {}
			for x in parsed_line.split(' '):
				x = x.split('=')
				x[1] = x[1][1:][:-1]
				_types[x[0]] = x[1]
			
			if 'rel' in _types:
				if _types['rel'] == 'stylesheet':
					with open(f'{template_path}/{_types["href"]}', 'r') as f:
						html_file[_index] = "<style>" + f.read() + "</style>"
		elif '<script ' in line:
			_script = {}
			_index += 1
			_line = re.search(r'<script(.+?)>', line)
			if _line:
				for i in _line.groups():
					i = i.split('=', 1)
					_script[i[0].strip()] = i[1][1:][:-1]
			if 'src' in _script:
				with open(f"{template_path}/{_script['src']}", 'r') as fp:
					html_file[_index] = "<script>" + fp.read() + "</script>"
		
		else:
			_index += 1


	return '\n'.join(html_file).encode()