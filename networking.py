import socket
import json
import threading
import time

class NetworkManager:
    def __init__(self, player_id, port=5005):
        self.player_id = player_id
        self.peers = {}
        self.running = True
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setblocking(False)
        try: self.sock.bind(('', self.port))
        except: pass

    def start(self):
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(2048)
                msg = json.loads(data.decode())
                if msg['id'] != self.player_id:
                    msg['last_seen'] = time.time()
                    self.peers[msg['id']] = msg
            except: pass
            time.sleep(0.01)

    def broadcast(self, state):
        state['id'] = self.player_id
        try:
            self.sock.sendto(json.dumps(state).encode(), ("255.255.255.255", self.port))
        except: pass