import time
from pynput import keyboard
from pynput.keyboard import Key

class HollowKnightController:
    def __init__(self):
        self.kb = keyboard.Controller()
        self.pressed_keys = set()
        
        # Hollow Knight key mappings
        self.key_map = {
            'jump': 'z',          # Jump
            'attack': 'x',        # Attack
            'focus': 'a',         # Focus/Heal
            'left': Key.left,     # Move left
            'right': Key.right,   # Move right
            'up' : Key.up,        # Look up (needed for attack up)
            'down': Key.down,     # Look down (need for attack down)  
            'load': "l",          # Quickslot (load), bind this in the debug mod binds menu
            'save': "s"           # Quickslot (save), bind this in the debug mod binds menu  
        }
        
        self.running = True
        
    def press_key(self, action):
        if action in self.key_map:
            key = self.key_map[action]
            if key not in self.pressed_keys:
                self.kb.press(key)
                self.pressed_keys.add(key)
                # print(f"Pressed: {action}")
    
    def release_key(self, action):
        if action in self.key_map:
            key = self.key_map[action]
            if key in self.pressed_keys:
                self.kb.release(key)
                self.pressed_keys.discard(key)
                # print(f"Released: {action}")
    
    def release_all(self):
        for key in self.pressed_keys.copy():
            self.kb.release(key)
        self.pressed_keys.clear()
        print("Released all keys")
    
    def output(self, nn_output: dict): #nn_output expects a dictionary of booleans
        # Press keys based on NN output
        for action, value in nn_output.items():
            if value: 
                self.press_key(action)
            else:
                self.release_key(action)
    
    def stop(self):
        self.release_all()
        self.running = False


if __name__ == "__main__":
    controller = HollowKnightController()
    
    print("Hollow Knight Controller Ready!")
    print("Test initializing in 3 seconds.")
    time.sleep(3)
    

    
    try:
        print("\n=== Testing Basic Movement ===")
        controller.output({
            "jump" : True,
            "left" : True,
            "right": False,
            "attack" : False,
            "focus" : False
        })
        
        controller.release_all()
        
    except KeyboardInterrupt: #^C stops the keyboard
        controller.stop()
        print("\nStopped by user")
