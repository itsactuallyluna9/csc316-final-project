from rich.live import Live
from rich.text import Text
from rich.spinner import Spinner
from rich.layout import Layout
from rich.panel import Panel
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


class Monitor:
    def __init__(self):
        self.counter = 0
        self.spawn_time = datetime.now().replace(microsecond=0)
        self.controller_input = [False,True,False,True,False,True] # up, left, down, right, jump, attack
        self.obs_status = 0 # 0 = unknown, 1 = recording, 2 = not recording, 3 = not connected
        self.create_layout()
    
    def create_layout(self):
        layout = Layout()
        layout.split_row(
            Layout(name="clock",size=None),
            Layout(name="controller_input", size=6),
            Layout(name="score"),
            Layout(name="recording_status", size=1),
            Layout(name="spinner", size=1),
        )
        layout["spinner"].update(Spinner("dots"))
        self.layout = layout
        self.update()
        
    def update(self):
        layout = self.layout

        alive_time = datetime.now().replace(microsecond=0) - self.spawn_time
        layout["clock"].update(f"[magenta]{alive_time}[/magenta]")
        layout["controller_input"].update(self.controller_input_text)
        # layout["body"].update(f"Counter: {self.counter}")
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
        main_text.append("↑", style="bold red" if self.controller_input[0] else "dim")
        main_text.append("←", style="bold red" if self.controller_input[1] else "dim")
        main_text.append("↓", style="bold red" if self.controller_input[2] else "dim")
        main_text.append("→", style="bold red" if self.controller_input[3] else "dim")
        main_text.append("!", style="bold red" if self.controller_input[4] else "dim")
        main_text.append("✀", style="bold red" if self.controller_input[5] else "dim")
        return main_text


def run_monitor() -> None:
    """
    Run the monitor producer: spawn a kitty kitten panel process and stream
    pickled monitor state to it over a unix-domain socket. The Monitor UI
    itself runs inside the panel process (see `--panel` mode below).
    """
    # socket path: XDG_RUNTIME_DIR or /tmp
    socket_path = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), f"csc316-monitor-{os.getuid()}.sock")

    class PanelProxy:
        """Helper to spawn the panel process and provide a send(state) method.

        Usage:
            proxy = PanelProxy(socket_path)
            proxy.start_panel()
            proxy.send(state_dict)
        """
        def __init__(self, socket_path: str):
            self.socket_path = socket_path
            self._srv = None
            self._conn = None
            self._lock = threading.Lock()
            self._thread = threading.Thread(target=self._server_loop, daemon=True)
            self._thread.start()

        def _server_loop(self):
            # ensure parent dir
            Path(self.socket_path).parent.mkdir(parents=True, exist_ok=True)
            try:
                if os.path.exists(self.socket_path):
                    os.unlink(self.socket_path)
            except Exception:
                pass
            srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            srv.bind(self.socket_path)
            srv.listen(1)
            self._srv = srv
            try:
                while True:
                    conn, _ = srv.accept()
                    with self._lock:
                        self._conn = conn
                    # block here until connection closes; keep reference so send() can use it
                    try:
                        while True:
                            # poll to detect closed connection; sleeps to avoid busy-loop
                            sleep(0.1)
                    except Exception:
                        pass
                    finally:
                        with self._lock:
                            try:
                                if self._conn:
                                    self._conn.close()
                            except Exception:
                                pass
                            self._conn = None
            finally:
                try:
                    srv.close()
                except Exception:
                    pass

        def start_panel(self):
            kitty = shutil.which("kitty")
            if not kitty:
                raise RuntimeError("kitty not found in PATH; cannot spawn panel")
            # The kitten command receives a command string to run inside the panel.
            # We run python module in unbuffered mode so output is immediate.
            cmd = f"python -u -m csc316_final_project.monitor --panel --socket {shlex.quote(self.socket_path)}"
            # Use kitten panel 'cmd' form
            subprocess.Popen([kitty, "kitten", "panel", cmd])

        def send(self, state: dict):
            payload = pickle.dumps(state)
            prefix = struct.pack("!I", len(payload))
            with self._lock:
                if not self._conn:
                    return False
                try:
                    self._conn.sendall(prefix + payload)
                    return True
                except (BrokenPipeError, ConnectionResetError, OSError):
                    try:
                        self._conn.close()
                    except Exception:
                        pass
                    self._conn = None
                    return False

    proxy = PanelProxy(socket_path)
    try:
        proxy.start_panel()
    except Exception as e:
        print(f"Failed to start panel: {e}")
        return

    # Example state source loop: update and send state continuously. In the
    # real application you'd update `state` from actual inputs.
    state = {
        "controller_input": [False, True, False, True, False, True],
        "obs_status": 0,
        "spawn_time": datetime.now().replace(microsecond=0).isoformat(),
        "counter": 0,
    }
    while True:
        state["counter"] += 1
        # Send; it's fine if there's no client yet (send returns False)
        proxy.send(state)
        sleep(0.1)


def run_panel(socket_path: str) -> None:
    """Run inside the kitten panel process: connect to the unix socket and
    render the Monitor UI using received state updates.
    """
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    # wait for socket to appear
    for _ in range(100):
        if Path(socket_path).exists():
            break
        sleep(0.05)
    else:
        print(f"Socket {socket_path} not found; exiting")
        return

    try:
        client.connect(socket_path)
    except Exception as e:
        print(f"Failed to connect to {socket_path}: {e}")
        return

    client.setblocking(True)
    buffer = b""

    with Live(refresh_per_second=10) as live:
        monitor = Monitor()
        while True:
            # read length-prefixed messages
            while len(buffer) < 4:
                chunk = client.recv(4096)
                if not chunk:
                    return
                buffer += chunk
            length = struct.unpack("!I", buffer[:4])[0]
            buffer = buffer[4:]
            while len(buffer) < length:
                chunk = client.recv(4096)
                if not chunk:
                    return
                buffer += chunk
            payload = buffer[:length]
            buffer = buffer[length:]
            try:
                state = pickle.loads(payload)
            except Exception:
                continue
            # apply state
            monitor.controller_input = state.get("controller_input", monitor.controller_input)
            monitor.obs_status = state.get("obs_status", monitor.obs_status)
            spawn_iso = state.get("spawn_time")
            if spawn_iso:
                try:
                    monitor.spawn_time = datetime.fromisoformat(spawn_iso)
                except Exception:
                    pass
            monitor.counter = state.get("counter", monitor.counter)
            live.update(monitor.update())
            sleep(0.05)


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
