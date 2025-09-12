import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from datetime import datetime, timedelta

from csc316_final_project.bridge import HKBridge

class HollowNN(nn.Module):
    def __init__(self, input_shape, num_actions):
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

def train(model: HollowNN, bridge: HKBridge, episodes=1000, gamma=0.99, lr=1e-4, max_episode_time=timedelta(minutes=5)):
    optimizer = optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    for episode in range(episodes):
        bridge.reset()
        state = bridge.get_state()
        done = False
        total_reward = 0
        start_time = datetime.now()

        while not done:
            state_tensor = torch.FloatTensor(state).unsqueeze(0)  # Add batch dimension
            q_values = model(state_tensor)
            action = torch.argmax(q_values).item()

            bridge.send_input({'action': action})
            next_state, reward, done = bridge.get_state()
            if datetime.now() - start_time > max_episode_time:
                done = True  # End episode if it exceeds max time

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
    input_shape = (3, 84, 84)  # Example input shape (C, H, W)
    num_actions = 4      # Example number of actions
    model = HollowNN(input_shape, num_actions)
    bridge = HKBridge(host='localhost', port=9999)
    try:
        train(model, bridge)
    finally:
        bridge.close()
