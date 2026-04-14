import socket
import json
import threading
import time

class NetworkManager:
    def __init__(self, player_id, port=5005):
        self.player_id = player_id
        self.peers = {} 
        self.port = port
        self.running = True
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # This makes the socket throw an error if we try to read an empty buffer
        self.sock.setblocking(False) 
        
        try:
            self.sock.bind(('', self.port))
        except Exception as e:
            print(f"Network Bind Error: {e}")

    def start(self):
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        while self.running:
            # --- THE FIX: DRAIN THE BUFFER ---
            while True:
                try:
                    data, addr = self.sock.recvfrom(2048)
                    msg = json.loads(data.decode())
                    if msg['id'] != self.player_id:
                        msg['last_seen'] = time.time()
                        self.peers[msg['id']] = msg
                except:
                    # When the buffer is completely empty, it throws an error.
                    # We catch it and break out of the reading loop.
                    break
            
            # Clean up old peers
            now = time.time()
            self.peers = {pid: p for pid, p in self.peers.items() if now - p['last_seen'] < 3}
            time.sleep(0.01)

    def broadcast(self, state):
        state['id'] = self.player_id
        msg = json.dumps(state).encode()
        
        # Aggressive Broadcast Strategy
        targets = [
            "<broadcast>",        
            "255.255.255.255",    
        ]
        
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            subnet_broadcast = local_ip.rsplit('.', 1)[0] + '.255'
            if subnet_broadcast not in targets:
                targets.append(subnet_broadcast)
        except:
            pass

        for target in targets:
            try:
                self.sock.sendto(msg, (target, self.port))
            except:
                pass
