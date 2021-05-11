# client.py

import socket

# to close a socket
#  1. identify the process using the socket
#     $> sudo lsof -i :65432
#     $> sudo kill [PID]1


HOST = '127.0.0.1'
PORT = 65432

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    options = ['1', 'q', 'exit']
    # exit = False
    while True:
        msg = input('enter option...')
        if msg in options:
            s.sendall(msg.encode(encoding='utf-8'))
            server_response = s.recv(1024)
            print(server_response.decode(encoding='utf-8'))
            if msg == 'exit':
                # exit = True
                break
        else:
            print('option selected not allowed')
    s.close()  # probably not needed
