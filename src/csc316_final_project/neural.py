from time import sleep
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from datetime import datetime, timedelta

from csc316_final_project.keyboard_emulation import HollowKnightController

class HollowNN(nn.Module):
    def __init__(self, input_shape, num_actions=7):
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

def train(model: HollowNN, bridge: HKBridge, controller: HollowKnightController, episodes=1000, gamma=0.99, lr=1e-4, max_episode_time=timedelta(minutes=5)):
    optimizer = optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    for episode in range(episodes):
        controller.press_key('load')
        # Wait a moment to load
        sleep(1)
        state = bridge.get_state()
        done = False
        total_reward = 0
        start_time = datetime.now()

        while not done:
            state_tensor = torch.FloatTensor(state).unsqueeze(0)  # Add batch dimension
            q_values = model(state_tensor)
            actions = q_values.detach() # left, right, up, down, jump, attack, focus

            controller.output(
                {
                    'left': actions[0][0] > 0,
                    'right': actions[0][1] > 0,
                    'up': actions[0][2] > 0,
                    'down': actions[0][3] > 0,
                    'jump': actions[0][4] > 0,
                    'attack': actions[0][5] > 0,
                    'focus': actions[0][6] > 0
                }
            )
            next_state, reward, done = bridge.get_state()
            if datetime.now() - start_time > max_episode_time or :
                done = True  # End episode if it exceeds max time

            reward = reward_function(next_state, state)
            total_reward += reward

            next_state_tensor = torch.FloatTensor(next_state).unsqueeze(0)
            next_q_values = model(next_state_tensor)
            max_next_q_value = torch.max(next_q_values).item()

            target_q_value = reward + (gamma * max_next_q_value * (1 - int(done)))
            target_q_values = q_values.clone().detach()
            target_q_values[0][action] = target_q_value

            loss = loss_fn(q_values, target_q_values)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            state = next_state

        print(f"Episode {episode+1}/{episodes}, Total Reward: {total_reward}")

if __name__ == "__main__":
    input_shape = (3, 84, 84)
    num_actions = 7
    model = HollowNN(input_shape, num_actions)
    controller = HollowKnightController()
    while not bridge.connected:
        print("Waiting for connection to game...")
        sleep(1)
    input("Press Enter to start training...")
    try:
        train(model, bridge, controller)
    finally:
        bridge.close()
