import socket
import pickle
import numpy as np
import pygame
import time
import rsa

# Your Network class
class Network:
    def __init__(self):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = "localhost"  # Change this to your server IP if needed
        self.port = 5555
        self.addr = (self.server, self.port)
        self.connect()

        # Generate RSA key pair for the client
        (self.client_public_key, self.client_private_key) = rsa.newkeys(512)

        # Send the client's public key to the server upon connection
        self.client.send(self.client_public_key.save_pkcs1())

    def connect(self):
        try:
            self.client.connect(self.addr)
        except socket.error as e:
            print("Unable to connect to server:", e)

    def send(self, data, server_public_key, receive=False):
        try:
            encrypted_data = rsa.encrypt(data.encode(), server_public_key)
            self.client.send(encrypted_data)
            if receive:
                data = self.client.recv(2048)
                if data.startswith(b"ENCRYPTED:"):
                    # Extract the encrypted message and remove the identifier
                    encrypted_message = data.split(b"ENCRYPTED:")[1]
                    decrypted_message = rsa.decrypt(encrypted_message, self.client_private_key).decode()
                    print("Received message:", decrypted_message)
                    return self.client.recv(2048).decode() # return the game state after the message
                else: 
                    return data.decode()
            else:
                return None
        except socket.error as e:
            print(e)

    def recv(self):
        try:
            return self.client.recv(20480).decode()
        except socket.timeout:
            return None
    
# Constants for game window and grid
width = 500
height = 500
rows = 20

# Colors for the game
rgb_colors = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
}
rgb_colors_list = list(rgb_colors.values())

# Function to draw the grid
def drawGrid(w, surface):
    global rows
    sizeBtwn = w // rows

    x = 0
    y = 0
    for l in range(rows):
        x = x + sizeBtwn
        y = y + sizeBtwn

        pygame.draw.line(surface, (255, 255, 255), (x, 0), (x, w))
        pygame.draw.line(surface, (255, 255, 255), (0, y), (w, y))

# Function to draw game elements
def drawThings(surface, positions, color=None, eye=False):
    global width, rgb_colors_list
    dis = width // rows
    if color is None:
        color = (np.random.randint(0, 255), np.random.randint(0, 255), np.random.randint(0, 255))
    for pos_id, pos in enumerate(positions):
        i, j = pos

        pygame.draw.rect(surface, color, (i * dis + 1, j * dis + 1, dis - 2, dis - 2))
        if eye and pos_id == 0:
            centre = dis // 2
            radius = 3
            circleMiddle = (i * dis + centre - radius, j * dis + 8)
            circleMiddle2 = (i * dis + dis - radius * 2, j * dis + 8)
            pygame.draw.circle(surface, (0, 0, 0), circleMiddle, radius)
            pygame.draw.circle(surface, (0, 0, 0), circleMiddle2, radius)

# Function to draw the game window
def draw(surface, players, snacks):
    global rgb_colors_list

    surface.fill((0, 0, 0))
    drawGrid(width, surface)
    for i, player in enumerate(players):
        color = rgb_colors_list[i % len(rgb_colors_list)]
        drawThings(surface, player, color=color, eye=True)
    drawThings(surface, snacks, (0, 255, 0))
    pygame.display.update()

# Main function for running the game
def main():
    win = pygame.display.set_mode((width, height))

    # Establish connection with the server
    n = Network()
    server_public_key = rsa.PublicKey.load_pkcs1(n.client.recv(2048))

    flag = True

    while flag:
        events = pygame.event.get() 
        pos = None
        if len(events) > 0:

            for event in events:
                if event.type == pygame.QUIT:
                    flag = False
                    pos = n.send("control:quit", server_public_key, receive=True)
                    pygame.quit()

                # Send control commands based on keyboard inputs
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        pos = n.send("control:left", server_public_key, receive=True)
                    elif event.key == pygame.K_RIGHT:
                        pos = n.send("control:right", server_public_key, receive=True)
                    elif event.key == pygame.K_UP:
                        pos = n.send("control:up", server_public_key, receive=True)
                    elif event.key == pygame.K_DOWN:
                        pos = n.send("control:down", server_public_key, receive=True)
                    elif event.key == pygame.K_SPACE:
                        pos = n.send("control:reset", server_public_key, receive=True)
                    elif event.key == pygame.K_z:
                        pos = n.send("message:Congratulations!", server_public_key, receive=True)
                    elif event.key == pygame.K_x:
                        pos = n.send("message:It works!", server_public_key, receive=True)
                    elif event.key == pygame.K_y:
                        pos = n.send("message:Ready?", server_public_key, receive=True)
        else:
            # If no events, send a "get" request to receive game state
            pos = n.send("control:get", server_public_key, receive=True)

        snacks, players = [], []
        
        # Parse the received position data for players and snacks
        if pos is not None:
            raw_players = pos.split("|")[0].split("**")
            raw_snacks = pos.split("|")[1].split("**")

            if raw_players == '':
                pass
            else:
                for raw_player in raw_players:
                    raw_positions = raw_player.split("*")
                    if len(raw_positions) == 0:
                        continue

                    positions = []
                    for raw_position in raw_positions:
                        if raw_position == "":
                            continue
                        nums = raw_position.split(')')[0].split('(')[1].split(',')
                        positions.append((int(nums[0]), int(nums[1])))
                    players.append(positions)

            if len(raw_snacks) == 0:
                continue

            for i in range(len(raw_snacks)):
                nums = raw_snacks[i].split(')')[0].split('(')[1].split(',')
                snacks.append((int(nums[0]), int(nums[1])))

        draw(win, players, snacks)


if __name__ == "__main__":
    main()
