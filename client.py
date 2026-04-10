import os, sys, math, time, ctypes
from engine import GameEngine
from networking import NetworkManager

IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    import msvcrt
    user32 = ctypes.windll.user32
    class Point(ctypes.Structure): _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
else:
    import termios, tty, select

class PloomClient:
    def __init__(self):
        self.engine = GameEngine("default.txt")
        self.net = NetworkManager(f"P_{os.getpid()}")
        self.paused = True
        self.running = True
        
        # Settings State
        self.show_fps = True
        self.fps_corner = "top-left" # options: top-left, top-right
        self.menu_index = 0
        self.menu_options = ["Resume", "Toggle FPS", "FPS Corner", "Exit"]

        # FPS Tracking
        self.frame_times = []
        
        # ANSI/Console Setup
        os.system("") 
        sys.stdout.write("\033[?25l\033[?1003h") 
        if IS_WINDOWS: user32.ShowCursor(False)
        else: self.old_settings = termios.tcgetattr(sys.stdin)
        
        self.net.start()

    def get_fps_color(self, fps):
        if fps < 30: return "\033[91m" # Red
        if fps < 55: return "\033[38;5;208m" # Orange
        return "\033[92m" # Green

    def handle_input(self):
        move_vec, rot_delta = [0, 0], 0

        if IS_WINDOWS:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\t': # TAB
                    self.paused = not self.paused
                    user32.ShowCursor(self.paused)
                elif self.paused:
                    if key == b'H': self.menu_index = (self.menu_index - 1) % len(self.menu_options) # Up
                    if key == b'P': self.menu_index = (self.menu_index + 1) % len(self.menu_options) # Down
                    if key == b'\r': # Enter
                        self.execute_menu()

            if not self.paused:
                pos = Point(); user32.GetCursorPos(ctypes.byref(pos))
                mx, my = user32.GetSystemMetrics(0)//2, user32.GetSystemMetrics(1)//2
                rot_delta = (pos.x - mx) * 0.003
                user32.SetCursorPos(mx, my)
                
                if user32.GetAsyncKeyState(0x57) & 0x8000: move_vec[0] = 1
                if user32.GetAsyncKeyState(0x53) & 0x8000: move_vec[0] = -1
                if user32.GetAsyncKeyState(0x41) & 0x8000: move_vec[1] = -1
                if user32.GetAsyncKeyState(0x44) & 0x8000: move_vec[1] = 1
        return move_vec, rot_delta

    def execute_menu(self):
        choice = self.menu_options[self.menu_index]
        if choice == "Resume": self.paused = False; user32.ShowCursor(False) if IS_WINDOWS else None
        elif choice == "Toggle FPS": self.show_fps = not self.show_fps
        elif choice == "FPS Corner": self.fps_corner = "top-right" if self.fps_corner == "top-left" else "top-left"
        elif choice == "Exit": self.running = False

    def render(self):
        try: cols, rows = os.get_terminal_size()
        except: cols, rows = 80, 24
        gh = rows - 2
        
        # Calculate FPS
        self.frame_times.append(time.time())
        self.frame_times = self.frame_times[-20:] # Keep last 20 frames
        fps = len(self.frame_times) / (self.frame_times[-1] - self.frame_times[0]) if len(self.frame_times) > 1 else 0

        if self.paused:
            # Render Menu
            output = []
            for i, opt in enumerate(self.menu_options):
                prefix = "> " if i == self.menu_index else "  "
                output.append(f"{prefix}{opt}".center(cols))
            
            # Vertical center
            pad = (gh - len(output)) // 2
            final_view = ([" " * cols] * pad) + output + ([" " * cols] * (gh - pad - len(output)))
            frame_str = "\n".join(final_view)
        else:
            # Raycasting Logic
            px, py, pa = self.engine.px, self.engine.py, self.engine.pa
            screen = []
            for x in range(cols):
                ray_a = (pa - 0.5) + (x/cols)
                vx, vy = math.cos(ray_a), math.sin(ray_a)
                d = 0.1
                while d < 14:
                    tx, ty = int(px + vx*d), int(py + vy*d)
                    if self.engine.map_data[ty * self.engine.map_size + tx] == '#': break
                    d += 0.1
                
                wh = int(gh / (d * math.cos(ray_a - pa) + 0.001))
                c = max(0, (gh-wh)//2)
                col = (" " * c) + ("█" * wh) + ("." * (gh-c-wh))
                screen.append(col[:gh])
            frame_str = "\n".join(["".join(r) for r in zip(*screen)])

        # Apply FPS overlay
        if self.show_fps:
            fps_text = f"{self.get_fps_color(fps)}{int(fps)} FPS\033[0m"
            if self.fps_corner == "top-left":
                frame_str = fps_text + frame_str[len(str(int(fps))) + 5:] # Crude overlay for demo
            else: # top-right
                # We'll prepend it to the first line using ANSI escapes
                frame_str = f"\033[s\033[1;{cols-10}H{fps_text}\033[u" + frame_str

        sys.stdout.write("\033[H" + frame_str + f"\nHP: {self.engine.health}%".center(cols))
        sys.stdout.flush()

    def run(self):
        try:
            while self.running:
                m, r = self.handle_input()
                self.engine.update(m, r)
                self.render()
                time.sleep(0.01)
        finally:
            sys.stdout.write("\033[?1003l\033[?25h\033[2J")

if __name__ == "__main__":
    PloomClient().run()
