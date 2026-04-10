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
        
        # Settings
        self.show_fps = True
        self.fps_corner = "top-left"
        self.menu_index = 0
        self.menu_options = ["Resume", "Toggle FPS", "FPS Corner", "Exit"]
        self.shades = " ░▒▓█"

        self.frame_times = []
        os.system("") 
        sys.stdout.write("\033[?25l\033[?1003h") 
        
        if IS_WINDOWS: user32.ShowCursor(True)
        else: self.old_settings = termios.tcgetattr(sys.stdin)
        
        self.net.start()

    def get_fps_color(self, fps):
        if fps < 30: return "\033[91m" 
        if fps < 55: return "\033[38;5;208m" 
        return "\033[92m"

    def handle_input(self):
        move_vec, rot_delta = [0, 0], 0

        if IS_WINDOWS:
            # BROAD BUFFER CLEAR: If we are playing, we don't want standard keys 
            # building up. We only care about Tab.
            while msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\t': # Tab detected
                    self.paused = not self.paused
                    user32.ShowCursor(self.paused)
                    # Warp mouse to center on unpause to prevent sudden snap
                    if not self.paused:
                        mx, my = user32.GetSystemMetrics(0)//2, user32.GetSystemMetrics(1)//2
                        user32.SetCursorPos(mx, my)
                elif self.paused:
                    # Arrow Keys in Windows Terminal
                    if key in (b'\xe0', b'\x00'):
                        sub = msvcrt.getch()
                        if sub == b'H': self.menu_index = (self.menu_index - 1) % len(self.menu_options)
                        if sub == b'P': self.menu_index = (self.menu_index + 1) % len(self.menu_options)
                    elif key == b'\r': self.execute_menu()

            if not self.paused:
                # 1. High-Performance Mouse Look
                pos = Point(); user32.GetCursorPos(ctypes.byref(pos))
                mx, my = user32.GetSystemMetrics(0)//2, user32.GetSystemMetrics(1)//2
                rot_delta = (pos.x - mx) * 0.003
                user32.SetCursorPos(mx, my)
                
                # 2. High-Performance Keyboard (Async)
                # Using 0x8000 check ensures we see the key even if the buffer is messy
                if user32.GetAsyncKeyState(0x57) & 0x8000: move_vec[0] = 1  # W
                if user32.GetAsyncKeyState(0x53) & 0x8000: move_vec[0] = -1 # S
                if user32.GetAsyncKeyState(0x41) & 0x8000: move_vec[1] = -1 # A
                if user32.GetAsyncKeyState(0x44) & 0x8000: move_vec[1] = 1  # D
        
        return move_vec, rot_delta

    def execute_menu(self):
        choice = self.menu_options[self.menu_index]
        if choice == "Resume": 
            self.paused = False
            if IS_WINDOWS: user32.ShowCursor(False)
        elif choice == "Toggle FPS": self.show_fps = not self.show_fps
        elif choice == "FPS Corner": self.fps_corner = "top-right" if self.fps_corner == "top-left" else "top-left"
        elif choice == "Exit": self.running = False

    def render(self):
        try: cols, rows = os.get_terminal_size()
        except: cols, rows = 80, 24
        gh = rows - 2
        
        # Calculate FPS
        t = time.time()
        self.frame_times.append(t)
        self.frame_times = [ft for ft in self.frame_times if t - ft < 1.0] # 1 sec window
        fps = len(self.frame_times)

        if self.paused:
            output = []
            for i, opt in enumerate(self.menu_options):
                prefix = "> " if i == self.menu_index else "  "
                line = f"{prefix}{opt}"
                if i == self.menu_index:
                    output.append(f"\033[7m {line.center(20)} \033[0m".center(cols + 8))
                else:
                    output.append(line.center(cols))
            
            pad = (gh - len(output)) // 2
            final_view = ([" " * cols] * pad) + output + ([" " * cols] * (gh - pad - len(output)))
            frame_str = "\n".join(final_view)
        else:
            # 3D Rendering with restored shading
            px, py, pa = self.engine.px, self.engine.py, self.engine.pa
            fov = self.engine.fov if hasattr(self.engine, 'fov') else math.pi/3.5
            screen_cols = []
            
            for x in range(cols):
                ray_a = (pa - fov/2) + (x/cols) * fov
                vx, vy = math.cos(ray_a), math.sin(ray_a)
                d, hit = 0.1, False
                while d < 16:
                    tx, ty = int(px + vx*d), int(py + vy*d)
                    if self.engine.map_data[ty * self.engine.map_size + tx] == '#':
                        hit = True; break
                    d += 0.05
                
                d_fixed = d * math.cos(ray_a - pa)
                wh = int(gh / (d_fixed + 0.001))
                c = max(0, (gh - wh) // 2)
                f = gh - c - wh
                
                # SHADING LOGIC: Index 4 (█) is closest, Index 1 (░) is furthest
                s_idx = max(1, min(4, int(5 * (1 - d/16))))
                char = self.shades[s_idx] if hit else " "
                
                col = (" " * c) + (char * wh) + ("." * max(0, f))
                screen_cols.append(col[:gh])
            
            frame_str = "\n".join(["".join(row) for row in zip(*screen_cols)])

        # HUD and FINAL PRINT
        hud = f" HP: {self.engine.health}% | [TAB] SETTINGS ".center(cols)
        
        # We print the world first
        sys.stdout.write("\033[H" + frame_str + "\n" + hud)

        # OVERLAY FPS AFTER THE WORLD (Guarantees it is visible)
        if self.show_fps:
            fps_color = self.get_fps_color(fps)
            fps_display = f"{fps_color}{fps} FPS\033[0m"
            if self.fps_corner == "top-left":
                sys.stdout.write(f"\033[1;1H{fps_display}")
            else:
                # Move cursor to top-right
                sys.stdout.write(f"\033[1;{cols-len(str(fps))-4}H{fps_display}")

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
            if IS_WINDOWS: user32.ShowCursor(True)

if __name__ == "__main__":
    PloomClient().run()
