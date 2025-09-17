from platform import system
import subprocess
import json

def acquire_idle_lock():
    """
    Acquire a system sleep lock to prevent the machine from idling during training.

    On Linux, this also disables shutdown and the power button.
    On macOS, this simply keeps the system awake.
    """
    match system():
        case "Linux":
            return subprocess.Popen(
                ["systemd-inhibit", "--what=idle:handle-power-key:shutdown", "--why=Training Model", "bash", "-c", "while true; do sleep 1; done"]
            )
        case "Darwin":
            return subprocess.Popen(["caffeinate", "-dims"])
        case _:
            print("Sleep lock not supported on this OS.")
            return None

def get_coords_of_active_window():
    match system():
        case "Linux":
            # hyprctl
            if subprocess.run(["which", "hyprctl"], capture_output=True).returncode == 0:
                result = subprocess.run(["hyprctl", "activewindow", "-j"], capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(f"hyprctl failed: {result.stderr.strip()}")
                try:
                    data = json.loads(result.stdout)
                    x = data["at"][0]
                    y = data["at"][1]
                    width = data["size"][0]
                    height = data["size"][1]
                    return (x, y, width, height)
                except json.JSONDecodeError as e:
                    raise RuntimeError(f"Failed to parse hyprctl output: {e}")
            else:
                raise RuntimeError("hyprctl not found in PATH; if you are not using Hyprland, this function is not implemented for your window manager. sorry!")
        case "Darwin":
            # AppleScript
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                tell frontApp
                    set win to front window
                    set {x, y} to position of win
                    set {w, h} to size of win
                    return {x, y, w, h}
                end tell
            end tell
            '''
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"osascript failed: {result.stderr.strip()}")
            try:
                x, y, w, h = map(int, result.stdout.strip().split(", "))
                return (x, y, w, h)
            except ValueError as e:
                raise RuntimeError(f"Failed to parse osascript output: {e}")
        case _:
            raise NotImplementedError("Active window coordinates not supported on this OS.")

class IdleLock:
    def __init__(self):
        self.process = None

    def __enter__(self):
        self.process = acquire_idle_lock()
        return self.process
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
