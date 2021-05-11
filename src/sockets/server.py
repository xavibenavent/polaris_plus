#!python3
# server.py

import socket
import threading

from src.pp_climanager import CLIManager

HOST = '127.0.0.1'
PORT = 65432


class Server:
    def __init__(self, clm: CLIManager):
        self.clm = clm
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((HOST, PORT))
        self.start_listening()

    def start_connection(self, conn, addr):
        with conn:
            print('connected by ', addr)
            options = ['0', '1', '2', '3', 'q', 'exit']
            while True:
                response = ''
                remote_user_input = conn.recv(1024).decode(encoding='utf-8')
                if remote_user_input in options:
                    print(remote_user_input)
                    response = f'option correct: {remote_user_input}'
                    self.clm.process(user_input=remote_user_input)
                else:
                    response = f'option not recognised: {remote_user_input}'
                conn.sendall(response.encode(encoding='utf-8'))
                if remote_user_input == 'exit' or not remote_user_input:
                    break
        print(f'connection with {addr} ended')

    def start_listening(self):
        conns_count = 0
        while True:
            print(f'\nserver listening at {HOST}:{PORT}')
            self.socket.listen()
            # accept() blocks
            conns_count += 1
            print(f'connections count: {conns_count}')
            conn, addr = self.socket.accept()
            x = threading.Thread(target=self.start_connection, args=(conn, addr))
            x.start()
