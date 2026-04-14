import socket
import json
import threading
import time

class NetworkManager:
    def __init__(self, player_id, port=5005):
        self.player_id = player_id
        self.peers = {} 
        self.known_ips = set() # We will store direct IPs here when we find them
        self.port = port
        self.running = True
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setblocking(False)
        
        try:
            self.sock.bind(('', self.port))
        except Exception as e:
            print(f"Network Bind Error: {e}")

    def start(self):
        threading.Thread(target=self._listen, daemon=True).start()
        threading.Thread(target=self._discovery_spray, daemon=True).start() # New Hole-Punching Thread

    def _discovery_spray(self):
        # Trick the firewall by sending an outbound packet to every single device on the local network
        while self.running:
            try:
                local_ip = socket.gethostbyname(socket.gethostname())
                base_ip = local_ip.rsplit('.', 1)[0] + '.'
                
                ping_msg = json.dumps({'id': self.player_id, 'ping': True}).encode()
                
                # Rapidly spray IPs 1 through 254
                for i in range(1, 255):
                    target = base_ip + str(i)
                    if target != local_ip:
                        try:
                            self.sock.sendto(ping_msg, (target, self.port))
                        except:
                            pass
            except:
                pass
            
            time.sleep(2) # Run the sweep every 2 seconds

    def _listen(self):
        while self.running:
            while True: # Drain the buffer to prevent lag
                try:
                    data, addr = self.sock.recvfrom(2048)
                    msg = json.loads(data.decode())
                    
                    if msg['id'] != self.player_id:
                        # We got a packet! Save their exact IP address so we can direct-message them
                        self.known_ips.add(addr[0])
                        
                        # Only update game state if it's not just a ping
                        if 'ping' not in msg:
                            msg['last_seen'] = time.time()
                            self.peers[msg['id']] = msg
                except:
                    break
            
            now = time.time()
            # Changed from 3 to 1.0 for faster vanishing on disconnect!
            self.peers = {pid: p for pid, p in self.peers.items() if now - p['last_seen'] < 1.0}
            time.sleep(0.01)

    def broadcast(self, state):
        state['id'] = self.player_id
        msg = json.dumps(state).encode()
        
        # Keep our broadcast targets just in case
        targets = set([
            "<broadcast>",        
            "255.255.255.255",    
        ])
        
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            subnet_broadcast = local_ip.rsplit('.', 1)[0] + '.255'
            targets.add(subnet_broadcast)
        except:
            pass

        # Add all the direct IPs we found during the discovery spray
        all_targets = list(targets) + list(self.known_ips)

        for target in all_targets:
            try:
                self.sock.sendto(msg, (target, self.port))
            except:
                pass
