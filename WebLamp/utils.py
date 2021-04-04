from datetime import datetime

http_status_codes = { # source of these can be found on https://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
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

# default_headers = {
# 	404: b'HTTP/1.1 404 Not Found\r\nContent-Type: application/json charset=utf-8\r\n\r\n{"404": "Not Found"}',
# 	405: b'HTTP/1.1 405 Method Not Allowed\r\nContent-Type: application/json charset=utf-8\r\n\r\n{"405": "Method Not Allowed"}'
# }

base = '\u001b[{}m'

class Style:
    Reset = 0
    Black = 30
    Red = 31
    Green = 32
    Yellow = 33
    Blue = 34
    Magenta = 35
    Cyan = 36
    White = 37

def log(msg: str, color: Style = Style.White) -> None:
    print(f'{base.format(color)}{datetime.now():%H:%M:%S}: {msg}{base.format(Style.White)}')