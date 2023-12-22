import socket
from _thread import *
import pickle
import numpy as np
import time
import rsa
from snake import SnakeGame
import uuid

# Server details
server = "localhost"
port = 5555
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Server setup
try:
    s.bind((server, port))
except socket.error as e:
    str(e)

s.listen(5)
print("Waiting for a connection, Server Started")

# Global variables
counter = 0
rows = 20
game = SnakeGame(rows)
game_state = ""
last_move_timestamp = time.time()
interval = 0.2
moves_queue = set()

# RSA key generation for server
(server_public_key, server_private_key) = rsa.newkeys(512)

# Maintain a dictionary to store client public keys
clients = {}

# Game colors
rgb_colors = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
}
rgb_colors_list = list(rgb_colors.values())

# Function to broadcast messages to clients
def brodcast_msg(msg):
    clients_to_remove = []
    for client_id, client_info in clients.items():
        if client_info['public_key']:
            try:
                encrypted_message = rsa.encrypt(msg.encode(), client_info['public_key'])
                client_info['conn'].send(b"ENCRYPTED:" + encrypted_message)
            except Exception as e:
                print(f"Error broadcasting to client {client_id}: {e}")
                clients_to_remove.append(client_id)


    for client_id in clients_to_remove:
        del clients[client_id]
        game.remove_player(client_id)

# Function running the game logic
def game_thread() : 
    global game, moves_queue, game_state 
    while True :
        last_move_timestamp = time.time()
        game.move(moves_queue)
        moves_queue = set()
        game_state = game.get_state()
        while time.time() - last_move_timestamp < interval : 
            time.sleep(0.2) 

# Function handling individual client connections
def client_thread(conn, addr, unique_id):
    global clients

    print("Player {} connected from {}".format(unique_id, addr))
    color = rgb_colors_list[np.random.randint(0, len(rgb_colors_list))]
    game.add_player(unique_id, color=color)

    # Send server's public key to the client
    conn.send(server_public_key.save_pkcs1())
    # Receive the client's public key
    client_public_key_pem = conn.recv(2048).decode()
    client_public_key = rsa.PublicKey.load_pkcs1(client_public_key_pem.encode())
    clients[unique_id] = {'conn': conn, 'public_key': client_public_key}

    try:
        while True:
            data = conn.recv(2048)

            if not data:
                print("No data received from client")
                break
            else:
                decrypted_data = rsa.decrypt(data, server_private_key).decode()

                if "control:" in decrypted_data: # Control input from the client
                    conn.send(game_state.encode())

                    # Handle control inputs
                    control_data = decrypted_data.split(":")[1]

                    if not control_data:
                        print("No data received from client")
                        break
                    elif control_data == "get":
                        print("Received get")
                        pass
                    elif control_data == "quit":
                        print("Received quit")
                        del clients[unique_id]
                        game.remove_player(unique_id)
                        conn.close()
                        break
                    elif control_data == "reset":
                        game.reset_player(unique_id)
                    elif control_data in ["up", "down", "left", "right"]:
                        move = control_data
                        moves_queue.add((unique_id, move))
                    else:
                        print("Invalid control data received from client:", control_data)
                elif "message:" in decrypted_data: # Public message from the client
                    # Handle public messages
                    message_data = decrypted_data.split(":")[1]
                    print("Received public message:", message_data)
                    brodcast_msg(message_data)
                    conn.send(game_state.encode())
                    
                else:
                    print("Invalid data received from client:", decrypted_data)

    except Exception as e:
        print(f"Player {unique_id} disconnected with error: {e}")

# Main function handling incoming connections
def main():
    global counter, game

    while True:
        conn, addr = s.accept()
        print("Connected to:", addr)

        unique_id = str(uuid.uuid4())

        start_new_thread(game_thread, ()) # Start the game thread for each client

        start_new_thread(client_thread, (conn, addr, unique_id)) # Start the client thread


if __name__ == "__main__":
    main()
