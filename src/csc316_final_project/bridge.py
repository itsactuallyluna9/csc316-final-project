import socket
import json
from dataclasses import dataclass
from .visualizer import GameStateVisualizer
import cv2

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

    def get_state(self) -> dict:
        """
        Get the current game state from the mod.
        
        Returns the game state dictionary.
        """
        message = json.dumps({'type': "get_state"}).encode('utf-8')
        self.sock.send(message)
        # wait for confirmation
        while True:
            data, _ = self.sock.recvfrom(1024*1024)
            response = json.loads(data.decode('utf-8'))
            if response.get('type') == 'state':
                return response
                break
        # raise NotImplementedError

    def close(self):
        self.sock.close()

if __name__ == "__main__":
    from time import sleep
    import sys
    
    print("Starting Hollow Knight Bridge Debug Viewer")
    print("Press 'q' to quit, 's' to save screenshot")
    print("=" * 50)
    
    bridge = None
    try:
        bridge = HKBridge()
        # Initialize visualizer with player-centered view and good scale
        vis = GameStateVisualizer(width=1200, height=800, scale=20.0)
        
        frame_count = 0
        while True:
            try:
                # Get current state
                state = bridge.get_state()
                print(f"Frame {frame_count}: Got state with {len(state.get('hitboxes', []))} hitboxes, {len(state.get('enemies', []))} enemies")
                
                # Visualize the state
                frame = vis.visualize_state(state)
                
                # Add frame counter
                cv2.putText(frame, f"Frame: {frame_count}", (10, 750), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Show the frame
                cv2.imshow("Hollow Knight Live View", frame)
                
                # Check for key press (1ms timeout)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("Quit key pressed")
                    break
                elif key == ord('s'):
                    # Save screenshot
                    filename = f"live_frame_{frame_count:04d}.png"
                    cv2.imwrite(filename, frame)
                    print(f"Saved {filename}")
                
                frame_count += 1
                sleep(0.033)  # ~30 FPS
                
            except KeyboardInterrupt:
                print("\nKeyboard interrupt received")
                break
            except Exception as e:
                print(f"Error getting/displaying state: {e}")
                sleep(1)  # Wait a bit before retrying
                
    except Exception as e:
        print(f"Failed to connect to game: {e}")
        print("Make sure the game is running with the SuperFancyInteropMod loaded")
        sys.exit(1)
    finally:
        if bridge is not None:
            try:
                bridge.close()
            except:
                pass
        cv2.destroyAllWindows()
        print("Bridge closed and windows destroyed")
