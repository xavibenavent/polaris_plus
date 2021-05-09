#!python3

import threading
from server import Server


def start_server():
    server = Server()


x = threading.Thread(target=start_server)
input('start server')
x.start()

while True:
    k = input('type a key...')
    print(k)



