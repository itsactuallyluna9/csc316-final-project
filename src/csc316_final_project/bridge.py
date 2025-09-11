import socket
import json

class HKBridge:
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_command(self, command, params=None):
        message = {'command': command}
        if params:
            message['params'] = params
        self.sock.sendto(json.dumps(message).encode(), (self.host, self.port))

    def close(self):
        self.sock.close()
