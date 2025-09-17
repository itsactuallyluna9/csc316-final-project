from rich.live import Live
from rich.text import Text
from rich.spinner import Spinner
from rich.layout import Layout
from rich.panel import Panel
from rich.console import Console
from datetime import datetime, timedelta
from time import sleep
import socket
import pickle
import os
import struct
import threading
import subprocess
import shutil
import shlex
import sys
from pathlib import Path

action_keys = ['left', 'right', 'up', 'down', 'jump', 'attack', 'focus']

class Monitor:
    def __init__(self):
        self.episode = 0
        self.reward = 0
        self.spawn_time = datetime.now().replace(microsecond=0)
        self.start_time = datetime.now().replace(microsecond=0)
        self.controller_input = {i: False for i in action_keys}
        self.obs_status = 0 # 0 = unknown, 1 = recording, 2 = not recording, 3 = not connected
        self.create_layout()
    
    def create_layout(self):
        layout = Layout()
        layout.split_row(
            Layout(name="spawn_clock",size=9),
            Layout(name="start_clock",size=9),
            Layout(name="controller_input", size=len(action_keys)*2),
            # Layout(name="padding", size=12),
            Layout(name="body"),
            Layout(name="recording_status", size=1),
            Layout(name="spinner", size=1),
        )
        # layout["padding"].update("") # just empty space
        layout["spinner"].update(Spinner("dots"))
        self.layout = layout
        self.update()
        
    def update(self):
        layout = self.layout

        alive_time = datetime.now().replace(microsecond=0) - self.spawn_time
        layout["spawn_clock"].update(f"[magenta]{alive_time}[/magenta]")
        run_time = datetime.now().replace(microsecond=0) - self.start_time
        layout["start_clock"].update(f"[cyan]{run_time}[/cyan]")
        layout["controller_input"].update(self.controller_input_text)
        layout["body"].update(f"[yellow]Episode: {self.episode}[/yellow] | Score: [green]{round(self.reward, 2)}[/green]")
        layout["recording_status"].update(self.obs_status_str)
        return layout
    
    @property
    def obs_status_str(self):
        match self.obs_status:
            case 1: return "[red]●[/]" # recording
            case 2: return "[cyan dim]*[/]" # not recording
            case 3: return "[dim]*[/]" # not connected
            case _: return "[yellow]?[/]" # unknown
    
    @property
    def controller_input_text(self):
        main_text = Text()
        main_text.append("↑", style="bold red" if self.controller_input["up"] else "dim")
        main_text.append("←", style="bold red" if self.controller_input["left"] else "dim")
        main_text.append("↓", style="bold red" if self.controller_input["down"] else "dim")
        main_text.append("→", style="bold red" if self.controller_input["right"] else "dim")
        main_text.append("!", style="bold red" if self.controller_input["jump"] else "dim")
        main_text.append("✀", style="bold red" if self.controller_input["attack"] else "dim")
        main_text.append("♥", style="bold red" if self.controller_input["focus"] else "dim")
        return main_text

def spawn_kitty_panel():
    """
    Spawns a kitty terminal panel for monitoring!

    Returns the subprocess.Popen object for the kitty terminal.
    """
    socket_path = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), f"csc316-monitor-{os.getuid()}.sock")
    print(["kitten", "panel", "--lines=1", "--edge=bottom", "/home/luna/.local/bin/uv", "run", "python3", "-u", "-m", "csc316_final_project.monitor", "--panel", "--socket", socket_path])
    # do nothing, im spawning it myself
    # return subprocess.Popen(["kitten", "panel", "--lines=1", "--edge=bottom", "/home/luna/.local/bin/uv", "run", "python3", "-u", "-m", "csc316_final_project.monitor", "--panel", "--socket", socket_path], cwd=Path(__file__).parent)

def send_info(state: dict) -> None:
    """
    Send state info to the monitor panel if running. This is a helper
    function you can call from anywhere in your code to update the monitor.
    """
    socket_path = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), f"csc316-monitor-{os.getuid()}.sock")
    if not os.path.exists(socket_path):
        return
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(socket_path)
        payload = pickle.dumps(state)
        prefix = struct.pack("!I", len(payload))
        client.sendall(prefix + payload)
        client.close()
    except Exception:
        pass

def run_panel(socket_path: str) -> None:
    """Run inside the kitten panel process: connect to the unix socket and
    render the Monitor UI using received state updates.
    """
    if os.path.exists(socket_path):
        os.unlink(socket_path)
    
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(socket_path)
        server.listen(5)  # Allow multiple pending connections
        server.settimeout(0.1)  # Non-blocking accept with timeout
        os.chmod(socket_path, 0o666) # allow other users to connect

        with Live(refresh_per_second=10) as live:
            monitor = Monitor()
            
            while True:
                # Try to accept new connections
                try:
                    client, _ = server.accept()
                    # Handle this client connection in a separate thread
                    def handle_client(client_sock):
                        try:
                            client_sock.setblocking(True)
                            buffer = b""
                            
                            # Read length-prefixed message
                            while len(buffer) < 4:
                                chunk = client_sock.recv(4096)
                                if not chunk:
                                    return
                                buffer += chunk
                            length = struct.unpack("!I", buffer[:4])[0]
                            buffer = buffer[4:]
                            while len(buffer) < length:
                                chunk = client_sock.recv(4096)
                                if not chunk:
                                    return
                                buffer += chunk
                            payload = buffer[:length]
                            
                            try:
                                state = pickle.loads(payload)
                                # Update monitor state
                                monitor.controller_input = state.get("controller_input", monitor.controller_input)
                                monitor.obs_status = state.get("obs_status", monitor.obs_status)
                                spawn_iso = state.get("spawn_time")
                                if spawn_iso:
                                    try:
                                        monitor.spawn_time = datetime.fromisoformat(spawn_iso)
                                    except Exception:
                                        pass
                                monitor.reward = state.get("reward", monitor.reward)
                                monitor.episode = state.get("episode", monitor.episode)
                                start_iso = state.get("start_time")
                                if start_iso:
                                    try:
                                        monitor.start_time = datetime.fromisoformat(start_iso)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                        finally:
                            client_sock.close()
                    
                    # Start thread to handle this client
                    thread = threading.Thread(target=handle_client, args=(client,), daemon=True)
                    thread.start()
                    
                except socket.timeout:
                    pass  # No new connection, continue
                except Exception:
                    pass  # Handle other socket errors gracefully
                
                # Update the Live display with the monitor
                live.update(monitor.update())
                sleep(0.05)
    finally:
        # Clean up socket file when done
        if os.path.exists(socket_path):
            os.unlink(socket_path)
        server.close()


def run_monitor() -> None:
    """Run the monitor in standalone mode - just display the UI without socket communication."""
    with Live(refresh_per_second=10) as live:
        monitor = Monitor()
        try:
            while True:
                live.update(monitor.update())
                sleep(0.1)
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    # CLI: when launched with --panel --socket <path> run as panel renderer.
    if '--panel' in sys.argv:
        # find socket arg
        sock = None
        if '--socket' in sys.argv:
            idx = sys.argv.index('--socket')
            if idx + 1 < len(sys.argv):
                sock = sys.argv[idx + 1]
        if not sock:
            print('No --socket provided for --panel mode; exiting')
            sys.exit(2)
        run_panel(sock)
    else:
        run_monitor()
