"""
Visualizer module for drawing game state data using OpenCV.
"""
import json
import cv2
import numpy as np
from typing import Dict, List, Tuple, Any


class GameStateVisualizer:
    """Visualizes Hollow Knight game state data using OpenCV."""
    
    def __init__(self, width: int = 1200, height: int = 800, scale: float = 10.0):
        """
        Initialize the visualizer.
        
        Args:
            width: Canvas width in pixels
            height: Canvas height in pixels  
            scale: Scaling factor for game coordinates to pixels
        """
        self.width = width
        self.height = height
        self.scale = scale
        self.canvas = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Camera position (world coordinates to center the view on)
        self.camera_x = 0.0
        self.camera_y = 0.0
        
        # Color definitions (BGR format for OpenCV)
        self.colors = {
            'Knight': (0, 255, 0),          # Green
            'Enemy': (0, 0, 255),           # Red
            'Attack': (0, 255, 255),   # Yellow
            'Terrain': (0, 255, 0),     # Green
            'Trigger': (255, 255, 0), # Cyan
            'Breakable': (255, 0, 255), # Magenta
            'Gate': (255, 0, 0), # Blue
            'HazardRespawn': (128, 0, 128), # Purple
            'Other': (128, 128, 128),  # Gray
            'background': (20, 20, 20),     # Dark gray
            'text': (255, 255, 255)         # White
        }
    
    def clear_canvas(self):
        """Clear the canvas to background color."""
        self.canvas.fill(0)
        self.canvas[:] = self.colors['background']
    
    def find_player_position(self, state_data: Dict[str, Any]) -> Tuple[float, float]:
        """
        Find the player's position in the game state.
        
        Args:
            state_data: Dictionary containing game state data
            
        Returns:
            Tuple of (player_x, player_y) or (0, 0) if not found
        """
        for hitbox in state_data.get('hitboxes', []):
            if hitbox.get('type') == 'Knight':
                bounds = hitbox['bounds']
                return bounds['x'], bounds['y']
        return 0.0, 0.0
    
    def center_camera_on_player(self, state_data: Dict[str, Any]):
        """
        Center the camera on the player position.
        
        Args:
            state_data: Dictionary containing game state data
        """
        player_x, player_y = self.find_player_position(state_data)
        self.camera_x = player_x
        self.camera_y = player_y
    
    def world_to_screen(self, x: float, y: float) -> Tuple[int, int]:
        """
        Convert world coordinates to screen coordinates.
        
        Args:
            x: World X coordinate
            y: World Y coordinate
            
        Returns:
            Tuple of (screen_x, screen_y)
        """
        # Apply camera offset and scale, then flip Y axis (game Y increases upward)
        screen_x = int((x - self.camera_x) * self.scale + self.width // 2)
        screen_y = int(self.height // 2 - (y - self.camera_y) * self.scale)
        return screen_x, screen_y
    
    def draw_rectangle(self, x: float, y: float, w: float, h: float, 
                      color: Tuple[int, int, int], thickness: int = 2):
        """
        Draw a rectangle at world coordinates.
        
        Args:
            x, y: Center position in world coordinates
            w, h: Width and height in world units
            color: BGR color tuple
            thickness: Line thickness (-1 for filled)
        """
        # Convert to screen coordinates
        center_x, center_y = self.world_to_screen(x, y)
        
        # Calculate rectangle bounds
        half_w = int(w * self.scale / 2)
        half_h = int(h * self.scale / 2)
        
        top_left = (center_x - half_w, center_y - half_h)
        bottom_right = (center_x + half_w, center_y + half_h)
        
        cv2.rectangle(self.canvas, top_left, bottom_right, color, thickness)
    
    def draw_circle(self, x: float, y: float, radius: float, 
                   color: Tuple[int, int, int], thickness: int = 2):
        """
        Draw a circle at world coordinates.
        
        Args:
            x, y: Center position in world coordinates
            radius: Radius in world units
            color: BGR color tuple
            thickness: Line thickness (-1 for filled)
        """
        center_x, center_y = self.world_to_screen(x, y)
        pixel_radius = int(radius * self.scale)
        cv2.circle(self.canvas, (center_x, center_y), pixel_radius, color, thickness)
    
    def draw_text(self, text: str, x: int, y: int, color: Tuple[int, int, int] | None = None,
                 font_scale: float = 0.6, thickness: int = 1):
        """
        Draw text at screen coordinates.
        
        Args:
            text: Text to draw
            x, y: Screen coordinates
            color: BGR color tuple
            font_scale: Font scale factor
            thickness: Text thickness
        """
        if color is None:
            color = self.colors['text']
        
        cv2.putText(self.canvas, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 
                   font_scale, color, thickness, cv2.LINE_AA)
    
    def draw_health_bar(self, health_data: Dict[str, int], x: int = 10, y: int = 30):
        """
        Draw player health bar in top-left corner.
        
        Args:
            health_data: Dictionary with 'current', 'max', and 'blue' health
            x, y: Screen position for health bar
        """
        current = health_data.get('current', 0)
        max_health = health_data.get('max', 5)
        blue = health_data.get('blue', 0)
        
        # Draw health text
        health_text = f"Health: {current}/{max_health}"
        if blue > 0:
            health_text += f" (+{blue} blue)"
        
        self.draw_text(health_text, x, y)
        
        # Draw health boxes
        box_size = 20
        spacing = 25
        start_y = y + 10
        
        for i in range(max_health):
            box_x = x + i * spacing
            box_color = self.colors['background']
            
            if i < current:
                box_color = (0, 255, 0)  # Green for current health
            elif i < current + blue:
                box_color = (255, 128, 0)  # Blue health
            else:
                box_color = (64, 64, 64)  # Dark gray for missing health
            
            cv2.rectangle(self.canvas, (box_x, start_y), 
                         (box_x + box_size, start_y + box_size), box_color, -1)
            cv2.rectangle(self.canvas, (box_x, start_y), 
                         (box_x + box_size, start_y + box_size), 
                         self.colors['text'], 1)
    
    def draw_hitbox(self, hitbox: Dict[str, Any]):
        """
        Draw a single hitbox.
        
        Args:
            hitbox: Dictionary containing hitbox data
        """
        bounds = hitbox['bounds']
        x, y = bounds['x'], bounds['y']
        w, h = bounds['w'], bounds['h']
        hitbox_type = hitbox.get('type', 'Other')
        name = hitbox.get('name', 'Unknown')
        
        color = self.colors.get(hitbox_type, self.colors['Other'])
        thickness = 1
        if hitbox_type == 'Knight':
            thickness = 3
        elif hitbox_type == 'Attack':
            thickness = 2

        self.draw_rectangle(x, y, w, h, color, thickness)
        
        if hitbox_type in ['Knight', 'Attack', 'Enemy']:
            screen_x, screen_y = self.world_to_screen(x, y + h/2 + 1)
            label = f"{name} ({hitbox_type})"
            self.draw_text(label, screen_x - 30, screen_y, color, 0.4)
    
    def draw_enemy(self, enemy: Dict[str, Any]):
        """
        Draw a single enemy.
        
        Args:
            enemy: Dictionary containing enemy data
        """
        x, y = enemy['x'], enemy['y']
        w, h = enemy['w'], enemy['h']
        name = enemy['name']
        hp = enemy['hp']
        
        # Draw enemy rectangle
        self.draw_rectangle(x, y, w, h, self.colors['Enemy'], -1)
        
        # Draw enemy name and health
        screen_x, screen_y = self.world_to_screen(x, y + h/2 + 1.5)
        enemy_text = f"{name} (HP: {hp})"
        self.draw_text(enemy_text, screen_x - 40, screen_y, self.colors['Enemy'], 0.5)
    
    def visualize_state(self, state_data: Dict[str, Any]) -> np.ndarray:
        """
        Visualize a complete game state.
        
        Args:
            state_data: Dictionary containing game state data
            
        Returns:
            numpy array representing the visualization
        """
        # Center camera on player
        self.center_camera_on_player(state_data)
        
        self.clear_canvas()
        
        # Draw health bar
        if 'player_health' in state_data:
            self.draw_health_bar(state_data['player_health'])
        
        # Draw hitboxes
        if 'hitboxes' in state_data:
            for hitbox in state_data['hitboxes']:
                self.draw_hitbox(hitbox)
        
        # Draw enemies
        if 'enemies' in state_data:
            for enemy in state_data['enemies']:
                self.draw_enemy(enemy)
        
        # Add coordinate grid (optional)
        self.draw_coordinate_grid()
        
        # Add legend
        self.draw_legend()
        
        # Add camera info
        self.draw_camera_info()
        
        return self.canvas.copy()
    
    def draw_coordinate_grid(self, spacing: int = 50):
        """Draw a coordinate grid for reference."""
        # Vertical lines
        for i in range(0, self.width, spacing):
            cv2.line(self.canvas, (i, 0), (i, self.height), (40, 40, 40), 1)
        
        # Horizontal lines  
        for i in range(0, self.height, spacing):
            cv2.line(self.canvas, (0, i), (self.width, i), (40, 40, 40), 1)
        
        # Center lines
        cv2.line(self.canvas, (self.width//2, 0), (self.width//2, self.height), 
                (60, 60, 60), 2)
        cv2.line(self.canvas, (0, self.height//2), (self.width, self.height//2), 
                (60, 60, 60), 2)
    
    def draw_legend(self):
        """Draw a legend explaining the colors."""
        legend_x = self.width - 200
        legend_y = 30
        
        legend_items = [
            ("Knight", self.colors['Knight']),
            ("Enemy", self.colors['Enemy']),
            ("Attack", self.colors['Attack']),
            ("Terrain", self.colors['Terrain']),
            ("Trigger", self.colors['Trigger']),
            ("Breakable", self.colors['Breakable']),
            ("Gate", self.colors['Gate']),
            ("HazardRespawn", self.colors['HazardRespawn']),
            ("Other", self.colors['Other'])
        ]
        
        self.draw_text("Legend:", legend_x, legend_y)
        
        for i, (label, color) in enumerate(legend_items):
            y_pos = legend_y + 25 + i * 20
            # Draw color box
            cv2.rectangle(self.canvas, (legend_x, y_pos - 10), 
                         (legend_x + 15, y_pos), color, -1)
            # Draw label
            self.draw_text(label, legend_x + 20, y_pos, font_scale=0.4)
    
    def draw_camera_info(self):
        """Draw camera position information."""
        camera_text = f"Camera: ({self.camera_x:.1f}, {self.camera_y:.1f})"
        self.draw_text(camera_text, 10, self.height - 20, font_scale=0.5)


def draw_game_state(state_data: Dict[str, Any], 
                   width: int = 1200, height: int = 800, 
                   scale: float = 50.0) -> np.ndarray:
    """
    Convenience function to draw a single game state.
    
    Args:
        state_data: Dictionary containing game state data
        width: Canvas width in pixels
        height: Canvas height in pixels
        scale: Scaling factor for game coordinates
        
    Returns:
        numpy array representing the visualization
    """
    visualizer = GameStateVisualizer(width, height, scale)
    return visualizer.visualize_state(state_data)


def load_and_visualize_jsonl(file_path: str, frame_index: int = 0) -> np.ndarray:
    """
    Load a JSONL file and visualize a specific frame.
    
    Args:
        file_path: Path to the JSONL file
        frame_index: Index of the frame to visualize (0-based)
        
    Returns:
        numpy array representing the visualization
    """
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    if frame_index >= len(lines):
        raise IndexError(f"Frame index {frame_index} out of range. File has {len(lines)} frames.")
    
    # Parse the JSON line (note: the format seems to use single quotes, so we need eval)
    line = lines[frame_index].strip()
    try:
        state_data = json.loads(line.replace("'", '"'))
    except json.JSONDecodeError:
        # If JSON parsing fails, try eval (less safe but handles the single quote format)
        state_data = eval(line)
    
    return draw_game_state(state_data)


def create_video_from_jsonl(file_path: str, output_path: str = "game_visualization.mp4",
                           fps: int = 30, width: int = 1200, height: int = 800) -> None:
    """
    Create a video from all frames in a JSONL file.
    
    Args:
        file_path: Path to the JSONL file
        output_path: Path for the output video file
        fps: Frames per second for the video
        width: Canvas width in pixels
        height: Canvas height in pixels
    """
    # Initialize video writer
    fourcc = cv2.VideoWriter.fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    visualizer = GameStateVisualizer(width, height)
    
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
                
            try:
                # Parse the JSON line
                try:
                    state_data = json.loads(line.replace("'", '"'))
                except json.JSONDecodeError:
                    state_data = eval(line)
                
                # Create frame
                frame = visualizer.visualize_state(state_data)
                
                # Add frame number
                cv2.putText(frame, f"Frame: {line_num}", (10, height - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                
                # Write frame to video
                out.write(frame)
                
                print(f"Processed frame {line_num}")
                
            except Exception as e:
                print(f"Error processing line {line_num}: {e}")
                continue
    
    # Release everything
    out.release()
    print(f"Video saved to {output_path}")


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        frame_index = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        
        # Visualize a single frame
        frame = load_and_visualize_jsonl(file_path, frame_index)
        
        cv2.imshow(f'Game State - Frame {frame_index}', frame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        # Save the frame
        cv2.imwrite(f'game_state_frame_{frame_index}.png', frame)
        print(f"Frame saved as game_state_frame_{frame_index}.png")
    else:
        print("Usage: python visualizer.py <jsonl_file> [frame_index]")
