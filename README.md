# Lamp

Lamp is a socketserver / webserver in py. (Specifically Python3.8.0)

My goal for this project is to make something similar to flask with less limitations

such as sending your own headers, custom byte sending, and more coming.

Examples of using Lamp:

```py
from lamp import Lamp, Content

server = Lamp()

@server.route('/')
def home(ctx: Content) -> bytes:

	return b'Welcome to the Webserver!'


server.run()
```