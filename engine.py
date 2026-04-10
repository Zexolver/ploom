import math
import time
import os

class GameEngine:
    def __init__(self, map_name="default.txt"):
        self.map_size = 0
        self.map_data = self.load_map(map_name)
        self.px, self.py, self.pa = 2.0, 2.0, 0.0
        self.health = 100
        self.last_tick = time.time()
        self.fov = math.pi / 3.5

    def load_map(self, filename):
        path = os.path.join("maps", filename)
        if not os.path.exists(path):
            # Fallback map so the game doesn't crash if file is missing
            print(f"Warning: {filename} not found. Using fallback.")
            self.map_size = 5
            return "#####" + "#...#" + "#.#.#" + "#...#" + "#####"
        
        with open(path, "r") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        self.map_size = len(lines)
        return "".join(lines)

    def update(self, move_vec, rot_delta):
        now = time.time()
        dt = now - self.last_tick
        self.last_tick = now

        self.pa += rot_delta
        speed = 5.0 * dt
        
        for move_speed, angle_off in [(move_vec[0]*speed, 0), (move_vec[1]*speed, math.pi/2)]:
            nx = self.px + math.cos(self.pa + angle_off) * move_speed
            ny = self.py + math.sin(self.pa + angle_off) * move_speed
            
            # Collision logic
            if 0 <= nx < self.map_size and 0 <= ny < self.map_size:
                try:
                    if self.map_data[int(ny) * self.map_size + int(nx)] == '.':
                        self.px, self.py = nx, ny
                except IndexError:
                    pass

    def get_state(self):
        return {"x": self.px, "y": self.py, "a": self.pa, "hp": self.health}
