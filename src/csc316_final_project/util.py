from platform import system
import subprocess

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

def spawn_kitty_panel():
    """
    Spawns a kitty terminal panel for monitoring!

    Returns the subprocess.Popen object for the kitty terminal.
    """
    return subprocess.Popen(["kitten", "panel", "--lines=1", "--edge=bottom", "uv", "run", "python3", "-m", "csc316_final_project.monitor"])
