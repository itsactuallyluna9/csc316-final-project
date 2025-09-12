import socket
import json
from dataclasses import dataclass

@dataclass
class HKInput:
    left: bool = False
    right: bool = False
    jump: bool = False
    attack: bool = False

    def to_dict(self):
        return {
            'left': self.left,
            'right': self.right,
            'jump': self.jump,
            'attack': self.attack
        }

class HKBridge:
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.connect((self.host, self.port))

    def reset(self):
        """
        Reset the game state via the mod.
        
        Will block until the reset is complete.
        """
        message = json.dumps({'type': "reset"}).encode('utf-8')
        self.sock.send(message)
        # wait for confirmation
        while True:
            data, _ = self.sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            if response.get('type') == 'reset_done':
                break
        raise NotImplementedError
    
    def send_input(self, inputs: HKInput):
        # preprocess:
        if inputs.left and inputs.right:
            inputs.left = False
            inputs.right = False
        message = json.dumps(inputs.to_dict()).encode('utf-8')
        self.sock.send(message)

    def get_state(self) -> tuple[str, float, bool]:
        """
        Get the current game state from the mod.
        
        Returns a tuple of (state, reward, done).
        """
        raise NotImplementedError

    def close(self):
        self.sock.close()

if __name__ == "__main__":
    from time import sleep
    bridge = HKBridge()
    while True:
        bridge.send_input(HKInput(left=True))
        sleep(1)
        bridge.send_input(HKInput(right=True))
        sleep(1)
        bridge.send_input(HKInput(jump=True))
        sleep(1)
        bridge.send_input(HKInput(attack=True))
        sleep(1)
    bridge.close()
