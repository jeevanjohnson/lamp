# Lamp

An asynchronous webserver made with sockets in python!

Examples of using Lamp:

```py
from Weblamp import Domain, Lamp, Connection

server = Lamp()
domain = Domain(('your.domain.com', '127.0.0.1:5000')) 

@domain.add_route(path = '/', method = ['GET'])
async def home(con: Connection) -> tuple:
  return (200, b'Hello World!')

server.add_domain(domain)
server.run(
  bind = ('127.0.0.1', 5000)
)
```

1 unique thing about this webserver is you can use a regex in your route and domain!

```py
import re

from Weblamp import Domain, Lamp, Connection

server = Lamp()
domain = Domain(('your.domain.com', '127.0.0.1:5000')) 

@domain.add_route(path = re.compile(r'^/u/(?P<userid>[0-9]*)$'), method = ['GET'])
async def home(con: Connection) -> tuple:
    userid = conn.args['userid'] # this came from the regex that was provided
    
    return (200, userid.encode())

server.add_domain(domain)
server.run(
  bind = ('127.0.0.1', 5000)
)
```
