import os
import re
import sys
import socket
import asyncio
from typing import Any
from typing import Union
from colorama import Fore
from typing import Callable
from asyncio import AbstractEventLoop

from .utils import log
from .utils import Style
from .utils import http_status_codes

def write_response(code: int, body: bytes, headers: Union[tuple, list] = ()) -> bytes:
    resp = f'HTTP/1.1 {code} {http_status_codes.get(code)}\r\n'
    resp += f'Content-Length: {len(body)}\r\n'
    for header in headers:
        resp += header + '\r\n'

    resp += '\r\n'

    return resp.encode() + body

class Route:
    def __init__(self, path: Union[re.Pattern, str], 
                method: Union[list, tuple, set], 
                func: Callable) -> None:
        self.path = path
        self.methods = method
        self.func = func
    
    def match(self, path: str) -> Union[bool, dict]:
        if isinstance(self.path, re.Pattern):
            x = self.path.search(path)
            if not x:
                return
            
            args = x.groupdict()
            return args
        else:
            return self.path == path

class Domain:
    def __init__(self, domain: Union[re.Pattern, str, list, set, tuple]) -> None:
        if not isinstance(domain, (re.Pattern, str, list, set, tuple)):
            raise Exception(f'`domain` can not be this type! {type(domain)}')

        self.domain: Union[re.Pattern, str, list, set, tuple] = domain
        self.routes: list[Route] = []
    
    def add_route(self, path: Union[re.Pattern, str], method: Union[list, tuple, set]) -> Callable:
        def inner(func: Callable) -> Callable:
            self.routes.append(Route(path, method, func))
            return func
        return inner

    def match(self, domain: str) -> bool:
        if isinstance(self.domain, re.Pattern):
            x = self.domain.search(domain)
            if not x:
                return False
            
            return True
        elif isinstance(self.domain, (list, set, tuple)):
            return domain in self.domain
        else:
            return self.domain == domain

class Connection:
    def __init__(self, req: dict, args: dict = {}) -> None:
        self._req = req
        tmp = {k.lower().replace('-','_'): v for k, v in req.items()}
        self.__dict__.update(**tmp)
        self.args = args
    
    def __getitem__(self, key: Any) -> Any:
        return self.__dict__[key]

    def __contains__(self, item: Any) -> bool:
        return self.__dict__.__contains__(item)

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
        self.domains: list[Domain] = []
    
    def add_domain(self, domain: Domain) -> None:
        self.domains.append(domain)
    
    def parse(self, data: bytes) -> Connection:
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
        
        req['path'] = path
        req['method'] = method
        req['params'] = params
        req['http_vers'] = http_vers

        for header in headers[1:]:
            k, v = header.split(': ', 1)
            req[k] = v
    
        if 'Content-Type' in req:
            boundary = '--' + req['Content-Type'].split('; boundary=', 1)[1]
            req['multipart'] = Multipart(body, boundary)
        else:
            req['body'] = body
        
        return Connection(req)

    async def handle(self, client: socket.socket, loop: AbstractEventLoop):
        data = await loop.sock_recv(client, 1024)
        if not data:
            return
        req = self.parse(data)
        if 'content_length' in req:
            length = int(req.content_length)
            if length > 1024:
                data += await loop.sock_recv(client, length)
                req = self.parse(data)

        if not ('method' in req and 'path' in req and 'host' in req):
            await loop.sock_sendall(client, b'')
            client.close()
            return

        for domain in self.domains:
            
            if not domain.match(req.host):
                continue

            for route in domain.routes:
                if not (args := route.match(req.path)):
                    continue
                
                if isinstance(args, dict):
                    req.args = args

                if req.method not in route.methods:
                    continue
            
                resp: tuple = await route.func(req)
                resp: bytes = write_response(*resp)

                await loop.sock_sendall(client, resp)
                client.close()

                log(
                    msg = f'Path: {req.path} | Host: {req.host}, Method: {req.method}', 
                    color = Fore.GREEN
                )

                return
            
        # Custom error handlers?
        await loop.sock_sendall(client, write_response(404, b'Not Found'))
        client.close()
        log(
            msg = f'Path: {req.path} | Host: {req.host}, Method: {req.method}', 
            color = Fore.RED
        )
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
                        f"python{major}.{minor} -m pip install uvloop"
                        ))
                    
                    log('Using uvloop!', Fore.GREEN)

                if self.debug:
                    log('Debug mode is on!', Fore.GREEN)

                log(f'Running HTTP sever on {running}', Fore.GREEN)

                while True:
                    client, addr = await loop.sock_accept(s)
                    loop.create_task(self.handle(client, loop))
        
        asyncio.run(_run())