import os, sys, math, time, ctypes
from engine import GameEngine
from networking import NetworkManager

IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    import msvcrt
    user32 = ctypes.windll.user32
    class Point(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
else:
    import termios, tty, select

class PloomClient:
    def __init__(self):
        try:
            self.engine = GameEngine("default.txt")
        except Exception as e:
            print(f"Engine Load Error: {e}")
            sys.exit(1)
            
        self.net = NetworkManager(f"P_{os.getpid()}")
        self.paused = True
        self.running = True
        
        self.show_fps = True
        self.fps_corner = "top-left"
        self.menu_index = 0
        self.menu_options = ["Resume", "Toggle FPS", "FPS Corner", "Exit"]
        self.shades = " ░▒▓█"
        self.frame_times = []

        os.system("") # Enable ANSI on Windows
        sys.stdout.write("\033[?25l\033[?1003h") 
        
        if IS_WINDOWS: 
            user32.ShowCursor(True)
        else:
            self.old_settings = termios.tcgetattr(sys.stdin)
            
        self.net.start()

    def get_fps_color(self, fps):
        if fps < 30: return "\033[91m" 
        if fps < 55: return "\033[38;5;208m" 
        return "\033[92m"

    def handle_input(self):
        move_vec, rot_delta = [0, 0], 0
        if IS_WINDOWS:
            while msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b'\t':
                    self.paused = not self.paused
                    user32.ShowCursor(self.paused)
                    if not self.paused:
                        mx, my = user32.GetSystemMetrics(0)//2, user32.GetSystemMetrics(1)//2
                        user32.SetCursorPos(mx, my)
                elif self.paused:
                    if key in (b'\xe0', b'\x00'):
                        sub = msvcrt.getch()
                        if sub == b'H': self.menu_index = (self.menu_index - 1) % len(self.menu_options)
                        if sub == b'P': self.menu_index = (self.menu_index + 1) % len(self.menu_options)
                    elif key == b'\r': self.execute_menu()

            if not self.paused:
                pos = Point(); user32.GetCursorPos(ctypes.byref(pos))
                mx, my = user32.GetSystemMetrics(0)//2, user32.GetSystemMetrics(1)//2
                rot_delta = (pos.x - mx) * 0.003
                user32.SetCursorPos(mx, my)
                
                if user32.GetAsyncKeyState(0x57) & 0x8000: move_vec[0] = 1 # W
                if user32.GetAsyncKeyState(0x53) & 0x8000: move_vec[0] = -1 # S
                if user32.GetAsyncKeyState(0x41) & 0x8000: move_vec[1] = -1 # A
                if user32.GetAsyncKeyState(0x44) & 0x8000: move_vec[1] = 1  # D
        else:
            # Linux Barebones Keyboard Input
            tty.setraw(sys.stdin.fileno())
            while select.select([sys.stdin], [], [], 0)[0]:
                char = sys.stdin.read(1)
                if char == '\t': self.paused = not self.paused
                elif not self.paused:
                    if char == 'w': move_vec[0] = 1
                    if char == 's': move_vec[0] = -1
                    if char == 'a': move_vec[1] = -1
                    if char == 'd': move_vec[1] = 1
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

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
        
        t = time.time()
        self.frame_times.append(t)
        self.frame_times = [ft for ft in self.frame_times if t - ft < 1.0]
        fps = len(self.frame_times)

        if self.paused:
            peer_count = len(self.net.peers)
            status_line = f"PLAYERS ON LAN: {peer_count + 1}".center(cols)
            
            output = [status_line, ""]
            for i, opt in enumerate(self.menu_options):
                prefix = "> " if i == self.menu_index else "  "
                if i == self.menu_index:
                    output.append(f"\033[7m {prefix}{opt} \033[0m".center(cols + 8))
                else:
                    output.append(f"{prefix}{opt}".center(cols))
            
            pad = (gh - len(output)) // 2
            frame_str = "\n".join(([" " * cols] * pad) + output + ([" " * cols] * (gh - pad - len(output))))
        else:
            px, py, pa = self.engine.px, self.engine.py, self.engine.pa
            fov = self.engine.fov if hasattr(self.engine, 'fov') else math.pi/3.5
            screen_cols = []
            
            visible_peers = []
            for pid, p in self.net.peers.items():
                dx, dy = p['x'] - px, p['y'] - py
                dist = math.sqrt(dx*dx + dy*dy)
                angle = math.atan2(dy, dx) - pa
                while angle > math.pi: angle -= 2*math.pi
                while angle < -math.pi: angle += 2*math.pi
                if abs(angle) < fov:
                    visible_peers.append({'dist': dist, 'angle': angle})

            for x in range(cols):
                ray_a = (pa - fov/2) + (x/cols) * fov
                vx, vy = math.cos(ray_a), math.sin(ray_a)
                
                d, hit = 0.1, False
                while d < 16:
                    tx, ty = int(px + vx*d), int(py + vy*d)
                    if 0 <= tx < self.engine.map_size and 0 <= ty < self.engine.map_size:
                        if self.engine.map_data[ty * self.engine.map_size + tx] == '#':
                            hit = True; break
                    d += 0.05
                
                p_hit, p_dist = False, 0
                for p in visible_peers:
                    if abs(ray_a - (pa + p['angle'])) < (0.15 / p['dist']) and p['dist'] < d:
                        p_hit, p_dist = True, p['dist']
                        break

                d_final = (p_dist if p_hit else d) * math.cos(ray_a - pa)
                wh = int(gh / (d_final + 0.001))
                ceil = max(0, (gh - wh) // 2)
                
                if p_hit:
                    char = "\033[91m█\033[0m" # ANSI Red
                else:
                    s_idx = max(1, min(4, int(5 * (1 - d/16))))
                    char = self.shades[s_idx] if hit else " "
                
                col = (" " * ceil) + (char * wh) + ("." * max(0, gh - ceil - wh))
                screen_cols.append(col[:gh])
            
            frame_str = "\n".join(["".join(row) for row in zip(*screen_cols)])

        sys.stdout.write("\033[H" + frame_str + f"\nHP: {self.engine.health}% | PEERS: {len(self.net.peers)} | [TAB] MENU".center(cols))
        
        if self.show_fps:
            fps_color = self.get_fps_color(fps)
            coord = "1;1H" if self.fps_corner == "top-left" else f"1;{cols-7}H"
            sys.stdout.write(f"\033[{coord}{fps_color}{fps} FPS\033[0m")
        sys.stdout.flush()

    def run(self):
        try:
            while self.running:
                m, r = self.handle_input()
                self.engine.update(m, r)
                self.net.broadcast(self.engine.get_state())
                self.render()
                time.sleep(0.01)
        finally:
            sys.stdout.write("\033[?1003l\033[?25h\033[2J")
            if IS_WINDOWS: user32.ShowCursor(True)
            else: termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

if __name__ == "__main__":
    PloomClient().run()
