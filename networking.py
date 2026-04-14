import socket
import json
import threading
import time

class NetworkManager:
    def __init__(self, player_id, port=5005):
        self.player_id = player_id
        self.peers = {} # Format: {id: {x, y, last_seen}}
        self.port = port
        self.running = True
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setblocking(False)
        
        try:
            # Bind to all interfaces
            self.sock.bind(('', self.port))
        except Exception as e:
            print(f"Network Bind Error: {e}")

    def start(self):
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(2048)
                msg = json.loads(data.decode())
                if msg['id'] != self.player_id:
                    msg['last_seen'] = time.time()
                    self.peers[msg['id']] = msg
            except:
                pass
            
            # Clean up timed-out peers (older than 3 seconds)
            now = time.time()
            self.peers = {pid: p for pid, p in self.peers.items() if now - p['last_seen'] < 3}
            time.sleep(0.01)

    def broadcast(self, state):
        state['id'] = self.player_id
        try:
            # Send to the universal broadcast address
            self.sock.sendto(json.dumps(state).encode(), ("255.255.255.255", self.port))
        except:
            pass
