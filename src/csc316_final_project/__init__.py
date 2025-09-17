from time import sleep
import click
import torch

from csc316_final_project.keyboard_emulation import HollowKnightController
from csc316_final_project.neural import HollowNN, train_model
from csc316_final_project.object_detection import load_yolo_model
from csc316_final_project.obs import OBSBridge
from csc316_final_project.util import IdleLock

@click.group()
def cli() -> None:
    """Entry point for the csc316_final_project package."""
    pass

@cli.command()
@click.option('--previous', type=click.Path(exists=True, dir_okay=False), help='Path to a previously saved model to continue training from', required=False)
@click.option('--episodes', default=1000, help='Number of training episodes')
@click.option('--start-episode', default=0, help='Start at episode number (for continuing training from a saved model)')
@click.option('--obs', is_flag=True, help='Run with automatic OBS recordings')
@click.option('--obs-every-n', default=5, help='Record to OBS every N episodes')
@click.option('--monitor-panel', is_flag=True, help='Show the monitor panel during training')
def train(previous: str, episodes: int = 1000, start_episode: int = 0, obs=False, obs_every_n=5, monitor_panel=False) -> None:
    input_shape = (3, 84, 84)
    model = HollowNN(input_shape)
    if previous:
        model.load_state_dict(torch.load(str(previous)))
        print(f"Loaded model from {previous}")
    controller = HollowKnightController()
    fk_detect_model = load_yolo_model()
    obs_bridge = OBSBridge(record_every_n=obs_every_n) if obs else None

    input("Press Enter to start training...")
    print("Starting in 5 seconds!")
    sleep(3) # give user time to switch to game window!
    if monitor_panel:
        from csc316_final_project.monitor import spawn_kitty_panel
        spawn_kitty_panel()
    sleep(2)

    with IdleLock():
        train_model(model, controller, obs_bridge, fk_detect_model, episodes, start_episode=start_episode)

def run():
    pass

if __name__ == "__main__":
    cli()
