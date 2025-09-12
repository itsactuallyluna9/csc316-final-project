import socket
import json

class HKBridge:
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def reset(self):
        raise NotImplementedError
    
    def send_input(self, input_data):
        message = json.dumps(input_data).encode('utf-8')
        self.sock.sendto(message, (self.host, self.port))


    def close(self):
        self.sock.close()
