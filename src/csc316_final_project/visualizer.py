#!/usr/bin/env python3
"""
Hollow Knight Abstraction-style Visualizer

This script creates a real-time visualization similar to the Abstraction mod,
showing colored hitboxes for different game entities like the player, enemies,
terrain, attacks, etc.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import json
import socket
import threading
import time
import sys
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class HitboxType:
    """Represents a hitbox type with its associated color and depth."""
    color: Tuple[int, int, int]
    depth: int
    name: str

    @classmethod
    def from_string(cls, type_str: str) -> 'HitboxType':
        """Convert string type to HitboxType object."""
        return HITBOX_TYPES.get(type_str, HITBOX_TYPES['Other'])


# Color definitions matching the Abstraction mod
HITBOX_TYPES = {
    'Knight': HitboxType((255, 255, 0), 0, 'Knight'),          # yellow
    'Enemy': HitboxType((255, 0, 0), 1, 'Enemy'),              # bright red  
    'Attack': HitboxType((0, 255, 255), 2, 'Attack'),          # cyan  
    'Terrain': HitboxType((0, 255, 0), 3, 'Terrain'),          # bright green
    'Trigger': HitboxType((127, 127, 255), 4, 'Trigger'),      # blue
    'Breakable': HitboxType((255, 191, 204), 5, 'Breakable'),  # pink
    'Gate': HitboxType((0, 100, 255), 6, 'Gate'),              # blue
    'HazardRespawn': HitboxType((255, 0, 255), 7, 'HazardRespawn'),  # magenta
    'Other': HitboxType((255, 165, 0), 8, 'Other'),            # orange
}


# Remove unused dataclasses since we work directly with dict data
# @dataclass 
# class Hitbox:
# @dataclass
# class GameState:


class GameStateVisualizer:
    """Visualizer that works with the HKBridge for real-time game state rendering."""
    
    def __init__(self, width: int = 1200, height: int = 800, scale: float = 10.0):
        """Initialize the visualizer.
        
        Args:
            width: Window width in pixels
            height: Window height in pixels 
            scale: Pixels per game unit (for coordinate conversion)
        """
        self.width = width
        self.height = height
        self.scale = scale
        self.camera_x = 0.0
        self.camera_y = 0.0
        
        # Try to load a font, fallback to default if not available
        try:
            self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            self.small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            self.font = ImageFont.load_default()
            self.small_font = ImageFont.load_default()
    
    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """Convert world coordinates to screen coordinates."""
        # Center the camera on the player and flip Y axis (OpenCV Y increases downward)
        screen_x = int((world_x - self.camera_x) * self.scale + self.width // 2)
        screen_y = int(self.height // 2 - (world_y - self.camera_y) * self.scale)
        return screen_x, screen_y
    
    def draw_hitbox(self, img, hitbox):
        """Draw a single hitbox on the image"""
        bounds = hitbox.get('bounds', {})
        hitbox_type = hitbox.get('type', 'Unknown')
        
        # Extract bounds
        x = bounds.get('x', 0)
        y = bounds.get('y', 0)
        w = bounds.get('w', 0)
        h = bounds.get('h', 0)
        
        # Skip invalid or oversized hitboxes
        if w <= 0 or h <= 0 or w > 500 or h > 500:
            return
        
        # Convert world coordinates to screen coordinates
        screen_x1, screen_y1 = self.world_to_screen(x, y)
        screen_x2, screen_y2 = self.world_to_screen(x + w, y + h)
        
        # Skip if completely outside screen
        if (screen_x2 < 0 or screen_x1 >= self.width or 
            screen_y2 < 0 or screen_y1 >= self.height):
            return
        
        # Clamp to screen bounds
        screen_x1 = max(0, min(self.width - 1, int(screen_x1)))
        screen_y1 = max(0, min(self.height - 1, int(screen_y1)))
        screen_x2 = max(0, min(self.width - 1, int(screen_x2)))
        screen_y2 = max(0, min(self.height - 1, int(screen_y2)))
        
        # Choose color based on type
        if hitbox_type == 'Terrain':
            color = (0, 255, 0)  # Green
        elif hitbox_type == 'Enemy':
            color = (0, 0, 255)  # Red
        elif hitbox_type == 'Knight':
            color = (255, 255, 0)  # Yellow
        elif hitbox_type == 'Attack':
            color = (255, 0, 255)  # Magenta
        elif hitbox_type == 'Trigger':
            color = (0, 255, 255)  # Cyan
        else:
            color = (128, 128, 128)  # Gray
        
        # Draw rectangle
        cv2.rectangle(img, (screen_x1, screen_y1), (screen_x2, screen_y2), color, 1)
    
    def visualize_state(self, state: dict) -> np.ndarray:
        """Create a frame with all the visualizations from game state dict."""
        # Create black background
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Update camera - instead of following player exactly, show a wider area
        player_pos = state.get('player_position', {})
        if player_pos:
            # Center camera between player and nearby hitboxes for better view
            player_x = player_pos.get('x', self.camera_x)
            player_y = player_pos.get('y', self.camera_y)
            
            # Find the center of all reasonable hitboxes to show more context
            hitboxes = state.get('hitboxes', [])
            if hitboxes:
                valid_positions = []
                for hitbox in hitboxes:
                    bounds = hitbox.get('bounds', {})
                    x, y = bounds.get('x', 0), bounds.get('y', 0)
                    w, h = bounds.get('w', 0), bounds.get('h', 0)
                    
                    # Skip massive bounds and empty terrain
                    if w > 500 or h > 500:
                        continue
                    if w == 0 and h == 0 and hitbox.get('type') == 'Terrain':
                        continue
                    
                    # Only include hitboxes within reasonable distance of player
                    distance = ((x - player_x)**2 + (y - player_y)**2)**0.5
                    if distance < 150:  # Within 150 units
                        valid_positions.append((x, y))
                
                if valid_positions:
                    # Calculate center of nearby hitboxes and player
                    all_x = [pos[0] for pos in valid_positions] + [player_x]
                    all_y = [pos[1] for pos in valid_positions] + [player_y]
                    
                    center_x = sum(all_x) / len(all_x)
                    center_y = sum(all_y) / len(all_y)
                    
                    # Smoothly move camera towards this center
                    self.camera_x = self.camera_x * 0.9 + center_x * 0.1
                    self.camera_y = self.camera_y * 0.9 + center_y * 0.1
                else:
                    # Fallback to player position
                    self.camera_x = player_x
                    self.camera_y = player_y
            else:
                self.camera_x = player_x
                self.camera_y = player_y
        
        # Draw hitboxes if we have them
        hitboxes = state.get('hitboxes', [])
        if hitboxes:
            # Sort hitboxes by depth (lower depth drawn first/behind)
            def get_depth(hitbox):
                hitbox_type = hitbox.get('type', 'Other')
                return HITBOX_TYPES.get(hitbox_type, HITBOX_TYPES['Other']).depth
            
            sorted_hitboxes = sorted(hitboxes, key=get_depth)
            
            drawn_count = 0
            for hitbox in sorted_hitboxes:
                # Skip obviously bad hitboxes (like the massive bounds cage)
                bounds = hitbox.get('bounds', {})
                w, h = bounds.get('w', 0), bounds.get('h', 0)
                
                # Skip if too large (bounds cage type stuff)
                if w > 500 or h > 500:
                    continue
                    
                # Skip if zero size and it's terrain (these are just empty bounds)
                if w == 0 and h == 0 and hitbox.get('type') == 'Terrain':
                    continue
                
                self.draw_hitbox(img, hitbox)
                drawn_count += 1
        
        # Draw player crosshair
        player_pos = state.get('player_position', {})
        if player_pos:
            px, py = self.world_to_screen(player_pos.get('x', 0), player_pos.get('y', 0))
            if 0 <= px < self.width and 0 <= py < self.height:
                # Draw crosshair for player position
                cv2.line(img, (px-10, py), (px+10, py), (255, 255, 255), 2)
                cv2.line(img, (px, py-10), (px, py+10), (255, 255, 255), 2)
                cv2.circle(img, (px, py), 3, (255, 255, 0), -1)  # Yellow center dot
        
        # Convert to PIL for text drawing
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)
        
        # Draw UI elements
        self.draw_ui_pil(draw, state)
        self.draw_legend_pil(draw)
        
        # Draw instructions if no data
        if not state:
            self.draw_no_data_message(draw)
        
        # Convert back to OpenCV format
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    def draw_ui_pil(self, draw: Any, state: dict):
        """Draw UI elements using PIL."""
        if not state:
            return
            
        # Health display
        health = state.get('player_health', {})
        if health:
            health_text = f"Health: {health.get('current', '?')}/{health.get('max', '?')}"
            if health.get('blue', 0) > 0:
                health_text += f" (+{health['blue']} blue)"
            draw.text((10, 10), health_text, fill=(255, 255, 255), font=self.font)
        
        # Position display
        pos = state.get('player_position', {})
        if pos:
            pos_text = f"Position: ({pos.get('x', 0):.2f}, {pos.get('y', 0):.2f})"
            draw.text((10, 35), pos_text, fill=(255, 255, 255), font=self.font)
        
        # Camera info
        camera_text = f"Camera: ({self.camera_x:.2f}, {self.camera_y:.2f})"
        draw.text((10, 60), camera_text, fill=(255, 255, 255), font=self.font)
        
        # Scale info
        scale_text = f"Scale: {self.scale:.1f}x"
        draw.text((10, 85), scale_text, fill=(255, 255, 255), font=self.font)
        
        # Hitbox count by type
        hitboxes = state.get('hitboxes', [])
        y_offset = 110
        if hitboxes:
            type_counts = {}
            visible_counts = {}
            
            for hitbox in hitboxes:
                hitbox_type = hitbox.get('type', 'Other')
                type_counts[hitbox_type] = type_counts.get(hitbox_type, 0) + 1
                
                # Check if hitbox is potentially visible
                bounds = hitbox.get('bounds', {})
                x, y = bounds.get('x', 0), bounds.get('y', 0)
                w, h = bounds.get('w', 0), bounds.get('h', 0)
                
                # Simple visibility check (within reasonable distance from camera)
                distance_from_camera = ((x - self.camera_x)**2 + (y - self.camera_y)**2)**0.5
                if distance_from_camera < 100:  # Within 100 units of camera
                    visible_counts[hitbox_type] = visible_counts.get(hitbox_type, 0) + 1
            
            for hitbox_type, count in sorted(type_counts.items()):
                color = HITBOX_TYPES.get(hitbox_type, HITBOX_TYPES['Other']).color
                visible_count = visible_counts.get(hitbox_type, 0)
                count_text = f"{hitbox_type}: {count} ({visible_count} near)"
                draw.text((10, y_offset), count_text, fill=color, font=self.small_font)
                y_offset += 20
        
        # Enemy count
        enemies = state.get('enemies', [])
        if enemies:
            enemy_text = f"Enemies: {len(enemies)}"
            draw.text((10, y_offset), enemy_text, fill=(255, 100, 100), font=self.small_font)
            y_offset += 20
        
        # Debug info for total hitboxes
        total_hitboxes = len(hitboxes)
        # Calculate how many would be drawn (exclude massive bounds and empty terrain)
        drawable_count = 0
        for hitbox in hitboxes:
            bounds = hitbox.get('bounds', {})
            w, h = bounds.get('w', 0), bounds.get('h', 0)
            if w > 500 or h > 500:
                continue
            if w == 0 and h == 0 and hitbox.get('type') == 'Terrain':
                continue
            drawable_count += 1
            
        debug_text = f"Hitboxes: {total_hitboxes} total, {drawable_count} drawable"
        draw.text((10, y_offset), debug_text, fill=(200, 200, 200), font=self.small_font)
    
    def draw_legend_pil(self, draw: Any):
        """Draw a legend showing hitbox types and their colors using PIL."""
        legend_x = self.width - 200
        legend_y = 10
        
        draw.text((legend_x, legend_y), "Hitbox Types:", fill=(255, 255, 255), font=self.font)
        
        y_offset = legend_y + 25
        for hitbox_type in sorted(HITBOX_TYPES.values(), key=lambda x: x.depth):
            # Draw colored square
            color_rect = [legend_x, y_offset, legend_x + 12, y_offset + 12]
            draw.rectangle(color_rect, fill=hitbox_type.color, outline=(255, 255, 255))
            
            # Draw type name
            draw.text((legend_x + 18, y_offset - 2), hitbox_type.name, fill=(255, 255, 255), font=self.small_font)
            
            y_offset += 16
    
    def draw_no_data_message(self, draw: Any):
        """Draw a message when no data is available."""
        message = "Waiting for game data..."
        
        # Get text size for centering
        bbox = draw.textbbox((0, 0), message, font=self.font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (self.width - text_width) // 2
        y = (self.height - text_height) // 2
        
        draw.text((x, y), message, fill=(255, 255, 255), font=self.font)


def main():
    """Main entry point - creates a standalone read-only visualization window."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hollow Knight Abstraction-style Visualizer')
    parser.add_argument('--host', default='localhost', help='Host to connect to')
    parser.add_argument('--port', type=int, default=9999, help='Port to connect to')
    parser.add_argument('--width', type=int, default=1200, help='Window width')
    parser.add_argument('--height', type=int, default=800, help='Window height')
    parser.add_argument('--scale', type=float, default=15.0, help='Pixels per game unit')
    
    args = parser.parse_args()
    
    print("Starting Hollow Knight Abstraction Visualizer...")
    print(f"Connecting to {args.host}:{args.port}")
    print("Press 'q' to quit, 's' to save screenshot")
    print("=" * 50)
    
    # Import bridge here to avoid circular imports
    from .bridge import HKBridge
    
    bridge = None
    try:
        # Create bridge connection
        bridge = HKBridge(host=args.host, port=args.port, auto_listen=True)
        
        # Initialize visualizer
        visualizer = GameStateVisualizer(width=args.width, height=args.height, scale=args.scale)
        
        # Create window
        window_name = "Hollow Knight - Abstraction Visualizer"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, args.width, args.height)
        
        frame_count = 0
        last_data_time = time.time()
        
        print("Waiting for game connection...")
        
        while True:
            try:
                # Get current state from bridge
                state = bridge.get_state()
                
                if state:
                    last_data_time = time.time()
                    if frame_count % 60 == 0:  # Log every 60 frames (about once per second)
                        hitbox_count = len(state.get('hitboxes', []))
                        enemy_count = len(state.get('enemies', []))
                        print(f"Frame {frame_count}: {hitbox_count} hitboxes, {enemy_count} enemies")
                        
                        # Debug: show some hitbox types
                        hitboxes = state.get('hitboxes', [])
                        if hitboxes:
                            type_counts = {}
                            for hitbox in hitboxes:
                                hitbox_type = hitbox.get('type', 'Other')
                                type_counts[hitbox_type] = type_counts.get(hitbox_type, 0) + 1
                            print(f"  Hitbox types: {dict(sorted(type_counts.items()))}")
                            
                            # Show a few example hitboxes
                            for i, hitbox in enumerate(hitboxes[:3]):
                                bounds = hitbox.get('bounds', {})
                                print(f"  Example {i+1}: {hitbox.get('name', 'Unknown')} ({hitbox.get('type', 'Other')}) at ({bounds.get('x', 0):.1f}, {bounds.get('y', 0):.1f}) size ({bounds.get('w', 0):.1f}x{bounds.get('h', 0):.1f})")
                
                # Visualize the state (even if empty - shows waiting message)
                frame = visualizer.visualize_state(state)
                
                # Add connection status and frame info
                connection_status = "Connected" if bridge.connected else "Waiting for connection..."
                connection_color = (0, 255, 0) if bridge.connected else (0, 165, 255)  # Green if connected, orange if waiting
                
                cv2.putText(frame, connection_status, (10, args.height - 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, connection_color, 2)
                
                cv2.putText(frame, f"Frame: {frame_count}", (10, args.height - 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Show timeout warning if no data for a while
                if bridge.connected and time.time() - last_data_time > 5.0:
                    cv2.putText(frame, "No data received for 5+ seconds", (10, args.height - 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
                # Display the frame
                cv2.imshow(window_name, frame)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # 'q' or ESC
                    print("Quit key pressed")
                    break
                elif key == ord('s'):
                    # Save screenshot
                    filename = f"hk_abstraction_frame_{frame_count:04d}.png"
                    cv2.imwrite(filename, frame)
                    print(f"Saved screenshot: {filename}")
                
                frame_count += 1
                time.sleep(0.033)  # ~30 FPS
                
            except KeyboardInterrupt:
                print("\nKeyboard interrupt received")
                break
            except Exception as e:
                print(f"Error in visualization loop: {e}")
                time.sleep(1)  # Wait a bit before retrying
                
    except Exception as e:
        print(f"Failed to start visualizer: {e}")
        print("Make sure the game is running with the SuperFancyInteropMod loaded")
        return 1
    finally:
        if bridge is not None:
            try:
                bridge.close()
            except:
                pass
        cv2.destroyAllWindows()
        print("Visualizer closed")
    
    return 0


# For compatibility with bridge.py
HollowKnightVisualizer = GameStateVisualizer


if __name__ == '__main__':
    main()
