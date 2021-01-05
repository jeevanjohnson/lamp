# Lamp

An asynchronous webserver made with sockets! (Not Finished)

Examples of using Lamp:

```py
from WebLamp import Lamp, Connection

server = Lamp()

@server.route(route = '/', method = ['GET'])
async def home(conn: Connection) -> bytes:

    conn.set_status(200)
    conn.set_body(b'Hello World!')
    
    return conn.response

server.run(("127.0.0.1", 5000))
```

1 unique thing about this webserver is you can use a regex in your path/routes as show below

```py
from WebLamp import Lamp, Connection

server = Lamp()

@server.route(route = r'^/u/(?P<userid>[0-9]*)$', method = ['GET'])
async def home(conn: Connection) -> bytes:

    userid = conn.args['userid'] # this came from the regex that was provided

    conn.set_status(200)
    conn.set_body(f'{userid}'.encode())
    
    return conn.response

server.run(("127.0.0.1", 5000))
```
