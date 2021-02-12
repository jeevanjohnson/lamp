# Lamp

An asynchronous webserver made with sockets! (Not Finished)

Examples of using Lamp:

```py
from WebLamp import Lamp, Connection

server = Lamp()

@server.route(path = '/', method = ['GET'])
async def home(conn: Connection) -> tuple:

    return 200, b'Hello World!'

server.run(("127.0.0.1", 5000))
```

1 unique thing about this webserver is you can use a regex in your route and domain!

```py
from WebLamp import Lamp, Connection
import re

server = Lamp()

@server.route(path = re.compile(r'^/u/(?P<userid>[0-9]*)$'), method = ['GET'])
async def home(conn: Connection) -> tuple:

    userid = conn.args['userid'] # this came from the regex that was provided
    
    return 200, userid.encode()

server.run(("127.0.0.1", 5000))
```
