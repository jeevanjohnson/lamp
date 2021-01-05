import socket
import asyncio
from typing import Union
import os
import json
from .helper import http_status_codes, default_headers
from .utlies import printc, Colors
import re

class Connection:
    def __init__(self, request: dict, args: dict = {}) -> None:
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
        self.routes = {}
        self.error_handlers = {}

    def route(self, route: str, domain: Union[str, bool] = None, method: list = []):
        def inner(func):
            
            key = json.dumps({'route': route, 'domain': domain, 'method': method})

            self.routes[key] = func
            
            return func
        return inner

    def error_handler(self, code: int):
        def inner(func):

            self.routes[code] = func
            
            return func
        return inner
    
    #async def parse_multi(self, req):
    #    req['multipart'] = {}
    #    if 'Content-Type' not in req:
    #        return req
    #    
    #    boundary = '--' + req['Content-Type'].split('boundary=', 1)[1]
    #
    #    b = req['body'].split(boundary.encode())[1:-1]
    #    for part in b:
    #        part = part.split(b'\r\n', 3)
    #        name = part[1].split()[3].decode().split('=', 1)[1].strip('"')
    #        req['multipart'][name] = part[3]
    #    
    #    return req
    
    def parse_params(self, path: str):
        if '?' not in path:
            return path, {}

        p = (path := path.split('?', 1))[1].split('&')
        params = {}

        for param in p:
            key, value = param.split('=', 1)
            if value.isdecimal():
                try: value = int(value)
                except: value = float(value)
            
            params[key] = value
        
        return path[0], params
    
    async def parse(self, req):
        _index = 0
        parsed_req = {}
        req = req.split(b'\r\n\r\n', 1)
        for line in req[0].splitlines():
            if not _index:
                parsed_req['method'], parsed_req['path'], parsed_req ['http_vers'] = line.decode().split(' ')
                parsed_req['path'], parsed_req['params'] = self.parse_params(parsed_req['path'])
            else:
                line = line.decode().split(': ')
                parsed_req[line[0]] = line[1]
        
            _index += 1
        
        # parsed_req = await self.parse_multi(parsed_req) # Not yet
        parsed_req['body'] = req[1]
        return parsed_req

    async def handler(self, client, loop):
        _req = await loop.sock_recv(client, 1024)
        if not _req:
            return
        req = await self.parse(_req)
        if 'Content-Length' in req and int(req['Content-Length']) > 1024:
            _req += await loop.sock_recv(client, 1000000)
            req = await self.parse(_req)
        
        for key in self.routes:
            k = json.loads(key) # brained Lawl
            r = []
            args = {}
            # checks

            if k['route'][0] == '^':
                k['route'] = re.compile(k['route'])
                x = k['route'].match(req['path'])
                if x:
                    for K, V in x.groupdict().items():
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

            if k['domain']:
                if 'Host' in req and req['Host'] == k['domain']:
                    r.append(True)
                else:
                    r.append(False)
            
            if k['method']:
                if req['method'] in k['method']:
                    r.append(True)
                else:
                    r.append(False)
            
            if False in r or True not in r:
                printc(f"Unhandled Request for: {req['Host']} | {req['path']} | {req['method']} | {req['http_vers']}", Colors.Red)
                continue # still thinking
            else:
                printc(f"Request for: {req['Host']} | {req['path']} | {req['method']} | {req['http_vers']}", Colors.Green)
                await loop.sock_sendall(client,
                    await self.routes[key](Connection(req, args))
                )
                return

        if 404 in self.error_handlers:
            er = self.error_handlers[404](Connection(req))
        else:
            er = default_headers.get(404)

        await loop.sock_sendall(client, er)
        return

    def run(self, socket_type: Union[str, tuple]) -> None: # I need to find a better word for this
        """
        socket_type: str or tuple
            You can decide wheather you want your web server to be on a
            unix socket or a normal ip and port.
            Examples:
                run(socket_type = '/tmp/cover.sock') <- unix_socket
                run(socket_type = ("127.0.0.1", 5000)) <- ip and port
        """
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
                loop = asyncio.get_event_loop()
                sock.bind(socket_type)
                if isinstance(socket_type, str): os.chmod(socket_type, 0o777)
                sock.listen(5)
                sock.setblocking(False)
                
                print(f"Server is up and running on: {socket_type}") # unpack tuple

                while True:
                    client, addr = await loop.sock_accept(sock)
                    # await self.handler(client)
                    loop.create_task(self.handler(client, loop))
        
        asyncio.run(_run())