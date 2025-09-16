from time import sleep
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from datetime import datetime, timedelta
from PIL import Image, ImageGrab

from csc316_final_project.keyboard_emulation import HollowKnightController

class HollowNN(nn.Module):
    def __init__(self, input_shape, num_actions=7):
        # num_actions corresponds to: left, right, up, down, jump, attack, focus
        super().__init__()
        c, h, w = input_shape
        self.net = nn.Sequential(
            nn.Conv2d(c, 32, kernel_size=8, stride=4), nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=4, stride=2), nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, stride=1), nn.ReLU(),
            nn.Flatten(),
            nn.Linear(64 * 7 * 7, 512), nn.ReLU(),
            nn.Linear(512, num_actions)
        )

    def forward(self, x):
        return self.net(x) # how's that for a one-liner?

def reward_function(state, prev_state):
    # reward for dealing damage or healing,
    # punish for taking damage, and a small punish for time
    reward = 0
    if state['enemy_health'] < prev_state['enemy_health']:
        reward += (prev_state['enemy_health'] - state['enemy_health']) * 10 # 10xdamage dealt reward
    if state['player_health'] > prev_state['player_health']:
        reward += (state['player_health'] - prev_state['player_health']) * 5 # 5xhealth gained reward
    if state['player_health'] < prev_state['player_health']:
        reward -= (prev_state['player_health'] - state['player_health']) * 7 # 7xhealth lost penalty
    reward -= 0.1  # small time penalty to encourage faster completion
    return reward

def get_screen_and_state():
    # take a screenshot and process it into the state representation
    screenshot = ImageGrab.grab()
    screenshot = screenshot.resize((84, 84)).convert('RGB')
    screen = np.array(screenshot).transpose((2, 0, 1)) / 255.0  # Normalize to [0, 1]

    # TODO: Extract actual game state from screenshot
    # For now, return dummy state - you'll need to implement state extraction
    state = {
        'player_health': 1.0,  # placeholder
        'enemy_health': 1.0,   # placeholder
    }

    return screen, state

def train(model: HollowNN, controller: HollowKnightController, episodes=1000, gamma=0.99, lr=1e-4, max_episode_time=timedelta(minutes=5), epsilon=0.05, action_threshold=0.5):
    optimizer = optim.Adam(model.parameters(), lr=lr)
    action_keys = ['left', 'right', 'up', 'down', 'jump', 'attack', 'focus']
    num_actions = len(action_keys)

    for episode in range(episodes):
        controller.press_key('load')
        sleep(1)

        screen, state = get_screen_and_state()
        done = False
        total_reward = 0
        start_time = datetime.now()

        while not done:
            # prepare tensors
            state_tensor = torch.from_numpy(screen).unsqueeze(0).float()  # [1, C, H, W]
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

            # give the game a short time to update, then observe next state
            sleep(0.05) # about 20 FPS - not including overhead
            next_screen, next_state = get_screen_and_state()

            # check terminal conditions
            if datetime.now() - start_time > max_episode_time or next_state.get('player_health', 1) <= 0:
                done = True

            reward = reward_function(next_state, state)
            total_reward += reward

            # Fixed approach: Use binary cross-entropy for multi-label classification
            # Create target actions based on reward feedback
            target_actions = torch.tensor(actions, dtype=torch.float32).unsqueeze(0)
            
            # Adjust targets based on reward
            if reward > 0:
                # Positive reward: reinforce actions taken (keep targets as 1.0 for taken actions)
                pass
            elif reward < 0:
                # Negative reward: discourage actions taken (flip targets for taken actions)
                target_actions = 1.0 - target_actions
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
        if (episode + 1) % 10 == 0:
            torch.save(model.state_dict(), f"hollow_nn_episode_{episode+1}.pth")


if __name__ == "__main__":
    input_shape = (3, 84, 84)
    num_actions = 7
    model = HollowNN(input_shape, num_actions)
    controller = HollowKnightController()
    input("Press Enter to start training...")
    train(model, controller)
