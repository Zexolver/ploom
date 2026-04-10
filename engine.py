import math
import time

class GameEngine:
    def __init__(self, map_str, map_size):
        self.map = map_str
        self.map_size = map_size
        self.px, self.py, self.pa = 2.0, 2.0, 0.0
        self.health = 100
        self.last_tick = time.time()

    def update(self, move_vec, rot_delta):
        now = time.time()
        dt = now - self.last_tick
        self.last_tick = now

        self.pa += rot_delta
        speed = 5.0 * dt
        
        # move_vec: [Forward/Back, Strafe]
        for move_speed, angle_off in [(move_vec[0]*speed, 0), (move_vec[1]*speed, math.pi/2)]:
            nx = self.px + math.cos(self.pa + angle_off) * move_speed
            ny = self.py + math.sin(self.pa + angle_off) * move_speed
            
            if 0 <= nx < self.map_size and 0 <= ny < self.map_size:
                if self.map[int(ny) * self.map_size + int(nx)] == '.':
                    self.px, self.py = nx, ny

    def get_state(self):
        return {"x": self.px, "y": self.py, "a": self.pa, "hp": self.health}