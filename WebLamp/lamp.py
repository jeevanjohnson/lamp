from .helper import http_status_codes, default_headers
from .utlies import printc, Colors
from typing import Union
import asyncio
import socket
import uvloop
import json
import os
import re

class TemplateFolderNotFound(Exception):
    pass

class TemplateNotFound(Exception):
    pass

class MultiPart:
    def __init__(self) -> None:
        """
        Layout is just what data is representing, there indexes are 
        the same just one tell you info about the other
        """
        self.layout = []
        self.data = []

class Connection:
    def __init__(self, request: dict, args: dict = {}) -> None:
        __slots__ = ('request', '_response', 'args')
        self.request = request
        self._response = ['HTTP/1.1 {status_code} {status}\r\n', '', b'\r\n', b'']
        self.args = args
    
    def set_status(self, code: int) -> None:
        self._response[0] = self._response[0].format(status_code = code, status = http_status_codes.get(code))

    def add_header(self, key, value) -> None:
        self._response[1] += f'{key}: {value}\r\n'
    
    def set_body(self, body: bytes) -> None:
        self._response[3] = body

    @property
    def response(self):
        if 'Content-Length' not in self._response[1]:
            self._response[1] += f'Content-Length: {len(self._response[3])}\r\n'
        
        r = b''
        for x in self._response:
            r += x.encode() if not isinstance(x, bytes) else x
        
        return r

class Lamp:
    def __init__(self) -> None:
        __slots__ = (
            'routes', 'error_handlers',
            'templateDir', 'regex',
            'debug', 'uv'
        )
        self.routes = {}
        self.error_handlers = {}
        self.templateDir = './templates'
        self.regex = {
            'htmlVars': re.compile(r'\[\[(.*)\]\]'),
            'types': re.compile(r'^<(.*)>$')
        }
        self.debug = False
        self.uv = False
         
    def renderTemplate(self, file, **kwargs):
        """
        There are problably better implementations of 
        this type of stuff, but its always good to give
        it a try!
        """
        if not os.path.exists(self.templateDir):
            raise TemplateFolderNotFound()
        if not os.path.exists(f"{self.templateDir}/{file}"):
            raise TemplateNotFound()
        
        with open(f"{self.templateDir}/{file}", 'r') as f:
            html = f.read().splitlines() # get content of html file
            h = '\n'.join(html) # make a copy so py doesn't reference the html variable

        for index, line in enumerate(h.splitlines()): # read every line to see if we need to parse it
            
            if (x := self.regex['htmlVars'].findall(line)):
                for v in x:
                    if (vv := v.strip()) in kwargs:
                        line = line.replace(f"[[{v}]]", kwargs[vv])
                html[index] = line

            if 'link' in line and (x := self.regex['types'].findall(line)):
                l = x[0].split()[1:]
                link = {k: v[1:][:-1] for k, v in [z.split('=', 1) for z in l]}
                if False not in [x in tuple(link) for x in ('type', 'rel', 'href')]:
                    if (link['type'], link['rel']) == ('css', 'stylesheet'):
                        with open(f"{self.templateDir}/{link.get('href')}", 'r') as css:
                            html[index] = '<style>' + css.read() + '</style>'
        
        return '\n'.join(html)

    def route(self, route: str, domain: Union[str, bool] = None, method: list = []):
        def inner(func):
            
            key = json.dumps({'route': str(route), 'domain': domain, 'method': method})

            self.routes[key] = func
            
            return func
        return inner

    def error_handler(self, code: int):
        def inner(func):

            self.routes[code] = func
            
            return func
        return inner
    
    def parse_multi(self, boundary: str, body: bytes) -> dict:
        multi = MultiPart()
        body = [x for x in body.split(boundary.encode()) if x and x != b'--\r\n']

        for arg in body:
            data = []
            layout = []

            arg, content = arg.split(b'\r\n\r\n', 1)
            arg = arg.decode().split('; ')[1:]

            for x in arg:
                x = x.split('=', 1)
                x[1] = x[1].strip('"')
                layout.append(x[0])
                data.append(x[1])

            layout.append('content')
            data.append(content)
            multi.layout.append(layout)
            multi.data.append(data)

        return multi
    
    async def parse(self, req: bytes) -> dict:
        r = {}
        req = req.split(b'\r\n\r\n', 1)
        for line in req[0].splitlines():
            if 'http_vers' not in r:
                r['method'], r['path'], r['http_vers'] = line.decode().split(' ')
                if '?' not in r['path']:
                    r['params'] = {}
                else:
                    r['path'], params = r['path'].split('?', 1)
                    r['params'] = {
                        k: v for k, v in [x.split('=', 1) for x in params.split('&')]
                    }
            else:
                line = line.decode().split(': ')
                r[line[0]] = line[1]
        
        if len(req) < 2:
            r['body'] = b''
        elif 'Content-Type' in r:
            boundary = '--' + r['Content-Type'].split('; boundary=', 1)[1]
            r['multipart'] = self.parse_multi(boundary, req[1])
        else:
            r['body'] = req[1]
        return r

    async def handler(self, client, loop):
        _req = await loop.sock_recv(client, 1024)
        if not _req:
            return
        req = await self.parse(_req)        
        if 'Content-Length' in req:
            c = int(req['Content-Length'])
            if c > 1024:
                _req += await loop.sock_recv(client, c)
                req = await self.parse(_req)

        for key in self.routes:
            k = json.loads(key)
            r = []
            args = {}

            if k['route'].startswith('re.compile'):
                x = {}
                exec('import re ; x = ' + k['route'], x)
                x = x['x'].match(req['path'])
                if x:
                    args = x.groupdict()
                    for K, V in args.items():
                        if not K or not V:
                            r.append(False)
                        else:
                            r.append(True)
                else:
                    r.append(False)
            else:
                if req['path'] == k['route']:
                    r.append(True)
                else:
                    r.append(False)
                
            if k['domain'] and 'Host' in req:
                if k['domain'].startswith('re.compile'):
                    exec('import re ; x = ' + k['domain'], (x := {}))
                    x = x.match(req['path'])
                    if x:
                        args = x.groupdict()
                        for K, V in args.items():
                            if not K or not V:
                                r.append(False)
                            else:
                                r.append(True)

                elif req['Host'] == k['domain']:
                    r.append(True)
                else:
                    r.append(False)

            if k['method']:
                if req['method'] in k['method']:
                    r.append(True)
                else:
                    r.append(False)
            
            if False in r or True not in r:
                continue
            else:
                if self.debug:
                    printc(f"{req['Host']} | {req['path']} | {req['method']} | {req['http_vers']}", Colors.Green)
                await loop.sock_sendall(client,
                    await self.routes[key](Connection(req, args))
                )
                return

        if self.debug:
            printc(f"{req['Host']} | {req['path']} | {req['method']} | {req['http_vers']}", Colors.Red)
        if 404 in self.error_handlers:
            er = self.error_handlers[404](Connection(req))
        else:
            er = default_headers.get(404)

        await loop.sock_sendall(client, er)
        return

    def run(self, socket_type: Union[str, tuple], **kwargs) -> None:
        """
        socket_type: str or tuple
            You can decide wheather you want your web server to be on a
            unix socket or a normal ip and port.
            Examples:
                run(socket_type = '/tmp/cover.sock') <- unix_socket
                run(socket_type = ("127.0.0.1", 5000)) <- ip and port
        
        debug: bool = False
            All this does for right now is print on the console
            all the request that are coming in, even the bad ones
        
        uvloop: bool = False
            Free speed pretty much.
        """
        self.debug = kwargs.get('debug', False)
        self.uv = kwargs.get('uvloop', False)

        if self.debug:
            printc('Debug Mode!', Colors.Green)

        async def _run():
            
            if not isinstance(socket_type, (str, tuple)):
                raise Exception('Only strings and tuples can be used for socket_type')

            if isinstance(socket_type, str):
                s = socket.AF_UNIX
                if os.path.exists(socket_type):
                    os.remove(socket_type)
            else:
                s = socket.AF_INET

            with socket.socket(s) as sock:
                if self.uv:
                    printc('Using uvloop!', Colors.Green)
                    uvloop.install()    
                loop = asyncio.get_event_loop()
                sock.bind(socket_type)
                if isinstance(socket_type, str): 
                    os.chmod(socket_type, 0o777)
                sock.listen(5)
                sock.setblocking(False)
                
                printc(f"Server is up and running on: {socket_type}", Colors.Green)

                while True:
                    client, addr = await loop.sock_accept(sock)
                    loop.create_task(self.handler(client, loop))
        
        asyncio.run(_run())