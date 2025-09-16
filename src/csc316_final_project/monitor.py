from rich.live import Live
from rich.text import Text
from rich.spinner import Spinner
from rich.layout import Layout
from rich.panel import Panel
from datetime import datetime, timedelta
from time import sleep
from multiprocessing import Process
import socket
import pickle


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
    with Live(refresh_per_second=10) as live:
        monitor = Monitor()
        while True:
            live.update(monitor.update())
            sleep(.1)
