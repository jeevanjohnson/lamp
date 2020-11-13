from socket import *
import handlers
import config
import asyncio

async def main():
	s = socket(AF_INET, SOCK_STREAM)

	s.bind((config.IP, config.PORT))      
	print(f"socket binded to {config.PORT}")

	s.listen(5)      
	print("socket is listening")   
	while True: 
	
		# Establish connection with client. 
		client, addr = s.accept()
	
		ServerObject = handlers.Handlers(
			client = client, 
			context = client.recv(config.PACKET_SIZE)
		)
		ServerObject.check()

asyncio.run(main())