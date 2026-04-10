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
        self.map_size = 16
        self.map_data = ("#" * 16) + (("#" + "." * 14 + "#") * 14) + ("#" * 16)
        self.engine = GameEngine(self.map_data, self.map_size)
        self.net = NetworkManager(f"P_{os.getpid()}")
        self.paused = True
        self.running = True
        self.last_mx = None
        
        # Standard ANSI sequences supported by almost all TTYs
        os.system("") 
        sys.stdout.write("\033[?25l")   # Hide cursor
        sys.stdout.write("\033[?1003h") # Enable Mouse Tracking
        sys.stdout.write("\033[?1015h") # Support for large coordinates
        sys.stdout.write("\033[?1006h") # SGR Mouse Mode (Best for TTY)
        
        if not IS_WINDOWS:
            self.old_settings = termios.tcgetattr(sys.stdin)

    def get_input(self):
        move_vec, rot_delta = [0, 0], 0

        if IS_WINDOWS:
            if msvcrt.kbhit():
                if msvcrt.getch() == b'\t': 
                    self.paused = not self.paused
                    user32.ShowCursor(self.paused)

            if not self.paused:
                # Desktop Cursor Locking
                mid_x = user32.GetSystemMetrics(0) // 2
                mid_y = user32.GetSystemMetrics(1) // 2
                pos = Point()
                user32.GetCursorPos(ctypes.byref(pos))
                rot_delta = (pos.x - mid_x) * 0.003
                user32.SetCursorPos(mid_x, mid_y)
                
                if user32.GetAsyncKeyState(0x57) & 0x8000: move_vec[0] = 1  # W
                if user32.GetAsyncKeyState(0x53) & 0x8000: move_vec[0] = -1 # S
                if user32.GetAsyncKeyState(0x41) & 0x8000: move_vec[1] = -1 # A
                if user32.GetAsyncKeyState(0x44) & 0x8000: move_vec[1] = 1  # D
        else:
            # Linux Barebones TTY Logic
            tty.setraw(sys.stdin.fileno())
            while select.select([sys.stdin], [], [], 0)[0]:
                char = sys.stdin.read(1)
                if char == '\t': self.paused = not self.paused
                elif char == '\x1b': # Escape Sequence
                    # Parse mouse sequence: \033[<0;X;Ym or M
                    seq = sys.stdin.read(2)
                    if '[' in seq:
                        full_seq = ""
                        while True:
                            c = sys.stdin.read(1)
                            full_seq += c
                            if c in 'mM': break
                        if not self.paused and ';' in full_seq:
                            parts = full_seq[1:-1].split(';')
                            curr_x = int(parts[1])
                            if self.last_mx is not None:
                                rot_delta = (curr_x - self.last_mx) * 0.05
                            self.last_mx = curr_x
                elif not self.paused:
                    if char == 'w': move_vec[0] = 1
                    if char == 's': move_vec[0] = -1
                    if char == 'a': move_vec[1] = -1
                    if char == 'd': move_vec[1] = 1
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

        return move_vec, rot_delta

    def render(self):
        try: cols, rows = os.get_terminal_size()
        except: cols, rows = 80, 24
        gh = rows - 2
        
        if self.paused:
            sys.stdout.write("\033[H" + " [PAUSED] - PRESS TAB ".center(cols * gh))
            return

        px, py, pa = self.engine.px, self.engine.py, self.engine.pa
        screen = []
        for x in range(cols):
            ray_a = (pa - 0.5) + (x/cols)
            vx, vy = math.cos(ray_a), math.sin(ray_a)
            d = 0.0
            while d < 12:
                d += 0.1
                if self.map_data[int(py+vy*d)*16 + int(px+vx*d)] == '#': break
            
            wh = int(gh / (d * math.cos(ray_a - pa) + 0.001))
            c = max(0, (gh - wh) // 2)
            col = (" " * c) + ("█" * wh) + ("." * (gh - c - wh))
            screen.append(col[:gh])
        
        output = "\n".join(["".join(r) for r in zip(*screen)])
        sys.stdout.write("\033[H" + output)
        sys.stdout.flush()

    def run(self):
        self.net.start()
        try:
            while self.running:
                m, r = self.get_input()
                self.engine.update(m, r)
                self.net.broadcast(self.engine.get_state())
                self.render()
                time.sleep(0.01)
        finally:
            sys.stdout.write("\033[?1003l\033[?25h\033[2J")
            if not IS_WINDOWS: termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)

if __name__ == "__main__":
    PloomClient().run()