import socket
import json
from threading import Thread
from .visualizer import GameStateVisualizer
import cv2

class HKBridge:
    def __init__(self, host='localhost', port=9999, auto_listen=True):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listening = False
        self.__listening_thread = Thread(target=self.listen, daemon=True)
        self.__internal_state = {}
        if auto_listen:
            self.listen_in_background()

    def listen_in_background(self):
        if not self.listening:
            self.__listening_thread.start()

    def listen(self):
        self.listening = True
        try:
            self.sock.bind((self.host, self.port))
            print(f"Listening for messages on {self.host}:{self.port}")
        except Exception as e:
            print(f"Failed to bind to {self.host}:{self.port}: {e}")
            return
            
        while self.listening:
            try:
                data, addr = self.sock.recvfrom(1024*1024)  # buffer size is 1MB
                try:
                    message = json.loads(data)
                    message_type = message.get("type")
                    
                    if message_type == "full_update":
                        self.__internal_state = message.get("state", {})
                    elif message_type == "partial_update":
                        updates = message.get("state", {})
                        self.__internal_state.update(updates)
                    else:
                        print(f"Unknown message type: {message_type}")
                        
                except json.JSONDecodeError as e:
                    print(f"Failed to decode JSON message: {e}")
                    continue
            except Exception as e:
                if self.listening:  # Only log if we're still supposed to be listening
                    print(f"Error receiving data: {e}")
                break

    def get_state(self) -> dict:
        """
        Get the current game state from the mod.
        
        Returns the game state dictionary.
        """
        return self.__internal_state
    
    @property
    def connected(self) -> bool:
        """
        Returns True if the bridge has received any state from the game (i.e., is connected).
        """
        return bool(self.__internal_state)

    def close(self):
        self.listening = False
        if self.sock:
            self.sock.close()
        # Wait for listening thread to finish (it's daemon so it will stop anyway)
        if self.__listening_thread.is_alive():
            self.__listening_thread.join(timeout=1.0)

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
