from asyncio import AbstractEventLoop
from .helper import http_status_codes
from .helper import default_headers
from typing import Callable
from .utils import Style
from typing import Union
from typing import Any
from .utils import log
import asyncio
import socket
import sys
import os
import re

def write_response(code: int, body: bytes, headers: Union[tuple, list] = ()) -> bytes:
    resp = f'HTTP/1.1 {code} {http_status_codes.get(code)}\r\n'
    resp += f'Content-Length: {len(body)}\r\n'
    for header in headers:
        resp += header + '\r\n'

    resp += '\r\n'

    return resp.encode() + body

class Connection:
    def __init__(self, req: dict, args: dict) -> None:
        self._req = req
        tmp = {k.lower().replace('-','_'): v for k, v in req.items()}
        self.__dict__.update(**tmp)
        self.args = args
    
    def __getitem__(self, key: Any) -> Any:
        return self._req[key]

class Multipart:
    def __init__(self, body: bytes, boundary: str) -> None:
        body = [x for x in body.split(boundary.encode()) if x and x != b'--\r\n']
        self.data = []
        self.layout = []
        for item in body:
            arg, content = item.split(b'\r\n\r\n', 1)
            for x in arg.decode().split('; '):
                if 'Content-Disposition' in x or '=' not in x:
                    continue

                k, v = x.split('=', 1)
                self.layout.append(k)
                self.data.append(v[1:][:-1])
            
            self.data.append(content[:-2])
            self.layout.append('data')

class Lamp:
    def __init__(self) -> None:
        self.error_handlers = {}
        self.debug = True
        self.routes = {}
        self.uv = False
    
    def error_handler(self, code: int) -> Callable:
        if not isinstance(code, int):
            raise Exception('Code must be an int!')
        def inner(func: Callable)  -> Callable:
            self.error_handler[code] = func
            return func
        return inner
    
    def route(self, path: Union[str, re.Pattern], 
             domain: Union[str, re.Pattern, bool] = None, 
             method: tuple = ()) -> Callable:
        def inner(func: Callable) -> Callable:
            nonlocal method
            if not isinstance(path, (str, re.Pattern)) or not isinstance(domain, (str, re.Pattern)):
                raise Exception(
                'Both `path` and `domain` need to be either a `str` '
                'or a `re.Pattern`'
                )
            
            if not isinstance(method, (list, tuple, set)):
                raise Exception('`method` must be a list, tuple, or a set.')
            
            if isinstance(method, (list, set)):
                method = tuple(method)

            self.routes[(path, domain, method)] = func
            return func
        return inner
    
    def parse(self, data: bytes) -> dict:
        req = {}
        headers, body = data.split(b'\r\n\r\n', 1)
        headers = headers.decode().splitlines()
        
        method, path, http_vers = headers[0].split()
        params = {}
        if '?' in path:
            split = path.split('?', 1)
            if len(split) == 2:
                path, _params = split
                for param in _params.split('&'):
                    if '=' not in param:
                        continue
                    
                    k, v = param.split('=', 1)
                    params[k] = v
        
        req.update({'method': method, 'path': path, 'params': params, 'http_vers': http_vers})

        for header in headers[1:]:
            k, v = header.split(': ', 1)
            req[k] = v
    
        if 'Content-Type' in req:
            boundary = '--' + req['Content-Type'].split('; boundary=', 1)[1]
            req['multipart'] = Multipart(body, boundary)
        else:
            req['body'] = body
        
        return req

    async def handle(self, client: socket.socket, loop: AbstractEventLoop) -> None:
        data = await loop.sock_recv(client, 1024)
        if not data:
            return
        req = self.parse(data)
        if 'Content-Length' in req:
            length = int(req['Content-Length'])
            if length > 1024:
                data += await loop.sock_recv(client, length)
                req = self.parse(data)
        
        for key, func in self.routes.items():
            path, domain, method = key
            args = {}

            if isinstance(path, re.Pattern):
                x = path.search(req['path'])
                if x:
                    args = x.groupdict()
                    for k, v in args.items():
                        if not k or not v:
                            continue
                else:
                    continue

            elif path != req['path']:
                continue
            
            if domain and 'Host' in req:
                if isinstance(domain, re.Pattern):
                    x = domain.search(req['Host'])
                    if x:
                        args = x.groupdict()
                        for k, v in args.items():
                            if not k or not v:
                                continue
                    else:
                        continue
                elif domain != req['Host']:
                    continue

            if method:
                if req['method'] not in method:
                    continue
            
            if self.debug:
                log('Path: {path} | Host: {Host} | Method: {method}'.format(**req), Style.Green)
            
            r = await func(Connection(req, args))
            r = write_response(*r)

            await loop.sock_sendall(client, r)
            client.close()
            return

        if self.debug:
            log('Path: {path} | Host: {Host} | Method: {method}'.format(**req), Style.Red)
        
        if 404 in self.error_handlers:
            r = write_response(*await self.error_handlers[404](Connection(req, args)))
        else:
            r = default_headers.get(404)
        
        await loop.sock_sendall(client, r)
        client.close()
        return

    def run(self, bind: Union[tuple, str], **kwargs) -> None:
        self.uv = kwargs.get('uvloop', False)
        self.debug = kwargs.get('debug', False)
        listen = kwargs.get('listen', 5)
        tasks = kwargs.get('tasks', [])
        
        async def _run():
            if not isinstance(bind, (tuple, str)):
                raise Exception('`bind` must be either a string or a tuple!')

            if isinstance(bind, tuple):
                running = 'IP: {}, PORT: {}'.format(*bind)
                sock = socket.AF_INET
            else:
                running = bind
                sock = socket.AF_UNIX
                if os.path.exists(bind):
                    os.remove(bind)
                
            with socket.socket(sock) as s:
                loop = asyncio.get_event_loop()

                for func in tasks:
                    asyncio.create_task(func())

                s.bind(bind)
                if isinstance(bind, str):
                    os.chmod(bind, 0o777)
                s.listen(listen)
                s.setblocking(False)

                if self.uv:
                    try: 
                        import uvloop
                        uvloop.install()
                    except ImportError:
                        major, minor = sys.version_info[:2]
                        raise ImportError((
                        "uvloop isn't installed! Please install by doing\n"
                        f"python{major}.{minor} -m pip install"
                        ))
                    
                    log('Using uvloop!', Style.Green)

                if self.debug:
                    log('Debug mode is on!', Style.Green)

                log(f'Running HTTP sever on {running}', Style.Green)

                while True:
                    client, addr = await loop.sock_accept(s)
                    loop.create_task(self.handle(client, loop))
        
        asyncio.run(_run())
