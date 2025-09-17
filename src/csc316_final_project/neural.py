from time import sleep
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from datetime import datetime, timedelta
from PIL import Image, ImageGrab
from functools import cache

from csc316_final_project.cv import get_player_health
from csc316_final_project.keyboard_emulation import HollowKnightController
from csc316_final_project.monitor import send_info
from csc316_final_project.object_detection import detect_fk_hit
from csc316_final_project.util import get_coords_of_active_window

class HollowNN(nn.Module):
    def __init__(self, input_shape, num_actions=7):
        # 7 (num_actions) corresponds to: left, right, up, down, jump, attack, focus
        super().__init__()
        c, h, w = input_shape
        conv = nn.Sequential(
            nn.Conv2d(c, 32, kernel_size=8, stride=4), nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2), nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1), nn.ReLU(),
            nn.Flatten()
        )
        with torch.no_grad():
            dummy = torch.zeros(1, c, h, w)
            conv_out = conv(dummy)
            conv_out_size = conv_out.shape[1]
        fc = nn.Sequential(
            nn.Linear(conv_out_size, 512), nn.ReLU(),
            nn.Linear(512, num_actions)
        )
        self.net = nn.Sequential(conv, fc)

    def forward(self, x):
        return self.net(x) # how's that for a one-liner?

def reward_function(state, prev_state):
    # reward for dealing damage or healing,
    # punish for taking damage, and a small punish for time
    reward = 0
    if state['enemy_damaged']:
        reward += 25 # 25xdamage dealt reward (since we don't track enemy health, we're giving it a flat reward)
    if state['player_health'] > prev_state['player_health']:
        # print("HEALED!")
        reward += (state['player_health'] - prev_state['player_health']) * 6.5 # 6.5xhealth gained reward
    if state['player_health'] < prev_state['player_health']:
        # print("HURT!" + str(prev_state['player_health'] - state['player_health']))
        reward -= (prev_state['player_health'] - state['player_health']) * 7 # 7xhealth lost penalty
    reward -= 0.005  # (really) small time penalty to encourage faster completion
    return reward

def get_screen_and_state(fk_detect_model):
    # take a screenshot and process it into the state representation
    window_bbox = get_coords_of_active_window()
    screenshot = ImageGrab.grab(bbox=window_bbox)

    screen = screenshot.resize((84, 84)).convert('RGB')
    screen = np.array(screen).transpose((2, 0, 1)) / 255.0  # Normalize to [0, 1]

    state = {
        'player_health': get_player_health(screenshot),
        'enemy_damaged': detect_fk_hit(screenshot, fk_detect_model)
    }

    return screen, state

def train_model(model: HollowNN, controller: HollowKnightController, obs_manager, fk_detect_model, episodes=1000, start_episode=0, gamma=0.99, lr=1e-4, max_episode_time=timedelta(minutes=5), epsilon=0.05, action_threshold=0.5):
    device = torch.accelerator.current_accelerator().type if torch.accelerator.is_available() else "cpu"
    model = model.to(device)
    print(f"Using {device} device")

    optimizer = optim.Adam(model.parameters(), lr=lr)
    action_keys = ['left', 'right', 'up', 'down', 'jump', 'attack', 'focus']
    num_actions = len(action_keys)
    send_info({'spawn_time': datetime.now().isoformat()})

    for episode in range(start_episode, episodes):
        if obs_manager:
            obs_manager.start_record(episode_num=episode)
        controller.press_key('load')
        send_info({'episode': episode, 'reward': 0, 'obs_status': obs_manager.status if obs_manager else 3, 'controller_input': {k: False for k in action_keys}, 'start_time': datetime.now().isoformat()})
        sleep(1)

        screen, state = get_screen_and_state(fk_detect_model)
        done = False
        total_reward = 0
        start_time = datetime.now()

        while not done:
            # prepare tensors
            state_tensor = torch.from_numpy(screen).unsqueeze(0).float().to(device)  # [1, C, H, W]
            q_values = model(state_tensor)  # [1, num_actions]

            # convert to probabilities (independent per-action) and choose multi-action (multi-hot)
            probs = torch.sigmoid(q_values).detach().cpu().numpy()[0]  # [num_actions]
            actions = probs > action_threshold  # greedy multi-label decision

            # epsilon exploration: with prob epsilon flip each action to a random boolean
            for i in range(num_actions):
                if np.random.rand() < epsilon:
                    actions[i] = np.random.rand() < 0.5

            # ensure at least one action (optional)
            # if not actions.any():
            #     actions[int(np.argmax(probs))] = True

            # map multi-hot actions to controller outputs
            controls = {k: False for k in action_keys}
            for i, key in enumerate(action_keys):
                if actions[i]:
                    controls[key] = True

            controller.output(controls)
            send_info({'controller_input': controls})

            # give the game a short time to update, then observe next state
            sleep(1/35)
            next_screen, next_state = get_screen_and_state(fk_detect_model)

            # fix: if we're in the first 5 seconds, don't punish for health loss (to avoid spawn invincibility issues and ui lag)
            if datetime.now() - start_time < timedelta(seconds=5):
                next_state['player_health'] = 5

            # check terminal conditions
            if datetime.now() - start_time > max_episode_time or next_state.get('player_health', 1) <= 0:
                done = True

            reward = reward_function(next_state, state)
            total_reward += reward
            send_info({'reward': total_reward})

            # Fixed approach: Use binary cross-entropy for multi-label classification
            # Create target actions based on reward feedback
            target_actions = torch.tensor(actions, dtype=torch.float32).unsqueeze(0).to(device)
            
            # Adjust targets based on reward
            if reward > 0:
                target_actions = torch.clamp(target_actions + 0.1, 0, 1)  # Encourage actions taken
            elif reward < 0:
                target_actions = torch.clamp(target_actions - 0.1, 0, 1)  # Discourage actions taken
            # If reward == 0, keep original targets
            
            # Use sigmoid activation and binary cross-entropy loss
            action_probs = torch.sigmoid(q_values)
            loss = torch.nn.functional.binary_cross_entropy(action_probs, target_actions)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            # advance to next step
            screen, state = next_screen, next_state

        print(f"Episode {episode+1}/{episodes}, Total Reward: {total_reward:.2f}")
        controller.release_all()
        send_info({'episode': episode, 'reward': total_reward, 'obs_status': obs_manager.status if obs_manager else 3, 'controller_input': {k: False for k in action_keys}})
        if (episode + 1) % 10 == 0:
            torch.save(model.state_dict(), f"hollow_nn_episode_{episode+1}.pth")
        sleep(5) # wait for the dying animation to finish
        if obs_manager:
            # sleep(0.5)
            obs_manager.stop_record()
    torch.save(model.state_dict(), f"hollow_nn_final_eps_{episodes}.pth")
