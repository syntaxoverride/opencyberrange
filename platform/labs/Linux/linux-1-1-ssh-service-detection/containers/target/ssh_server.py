#!/usr/bin/env python3
import socket
import paramiko
import threading
import sys
import traceback

class CustomSSHServer(paramiko.ServerInterface):
    def check_auth_password(self, username, password):
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password,publickey'

def handle_client(client_sock, addr):
    try:
        transport = paramiko.Transport(client_sock)
        transport.local_version = 'SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5 (Ubuntu Linux; protocol 2.0; flag: OCR{ssh_d3t3ct3d})'

        host_key = paramiko.RSAKey(filename='/opt/ssh-server/host_rsa_key')
        transport.add_server_key(host_key)

        server = CustomSSHServer()
        transport.start_server(server=server)

        channel = transport.accept(20)
        if channel:
            channel.close()
    except Exception as e:
        print(f'Error handling client: {e}', file=sys.stderr)
        traceback.print_exc()
    finally:
        try:
            transport.close()
        except:
            pass

def main():
    print('Starting SSH server...', flush=True)

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', 22))
        server_socket.listen(100)

        print('SSH Server listening on port 22', flush=True)

        while True:
            try:
                client_sock, addr = server_socket.accept()
                print(f'Connection from {addr}', flush=True)
                client_thread = threading.Thread(target=handle_client, args=(client_sock, addr))
                client_thread.daemon = True
                client_thread.start()
            except KeyboardInterrupt:
                print('Shutting down...', flush=True)
                break
            except Exception as e:
                print(f'Accept error: {e}', file=sys.stderr, flush=True)
                traceback.print_exc()
    except Exception as e:
        print(f'Fatal error: {e}', file=sys.stderr, flush=True)
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
