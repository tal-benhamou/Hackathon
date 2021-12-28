import socket
import struct
import msvcrt
import sys

import keyboard
import time
from select import select
# import readchar


class Client():

    def __init__(self, port, ip) -> None:
        self._port = port
        self._ip = ip
        self._teamName = "noName2"
        # self._socketTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self._socketUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        # self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # self._socketUDP.bind(('', 13117))  # dont change
        # self._socketTCP.settimeout(3)
        # self._socketTCP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.communicateWithServer()

    def communicateWithServer(self):
        print("Client started, listening for offer requests...")
        self._socketTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self._socketTCP.settimeout(3)
        self._socketUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._socketUDP.bind(('', 13117))  # dont change

        while True:
            try:
                # time.sleep(2)
                print("here")
                offer_from_server, ip = self._socketUDP.recvfrom(1024)
                print("here2")

            except:
                continue  # try again
            print(f"Received offer from {ip},attempting to connect...")
            magic_cookie, type, TCPort = struct.unpack(">IbH", offer_from_server)
            if (magic_cookie != int(0xabcddcba) or type != 2):
                print("if")
                continue  # try again
            break
        while True:
            try:
                print(f"TCPPORT = {TCPort}")
                self._socketTCP.connect((self._ip, TCPort))
                print("CONNECTED")
                break
            except:
                print("exceptClient")
                continue  # try again
        self.Game()

    def Game(self):
        # time.sleep(1)
        message = self._teamName + "\n"
        self._socketTCP.send(bytes(message, encoding='utf-8'))
        from_server = str(self._socketTCP.recv(1024), 'utf-8')
        # while (from_server == ''):
        #     try:
        #         from_server = str(self._socketTCP.recv(1024), 'utf-8')
        #     except:
        #         continue
        print(f"from_server = {from_server}")
        start_time = time.time()
        # user_input , stam, stam2 = select([keyboard.read_key()], [], [],10)
        print("press the answer")
        # user_input = keyboard.read_key()
        # readchar.readchar()

        # user_input = msvcrt.getch()
        # val = msvcrt
        # user_input = -1
        # try:
        user_input = keyboard.read_key()
            # user_input, a, b = select([keyboard.read_key()], [], [], 10)
        # except:
        #     pass
        # if (len(user_input) == 0):
        #     pass
        # else:
        print("client send answer to server")
        self._socketTCP.send(bytes(user_input[0], encoding='utf-8'))
        try:
            from_server = str(self._socketTCP.recv(1024), 'utf-8')
        except:
            pass
        print("HERE.!.!.")
        print(from_server)
        print("Server disconnected, listening for offer requests...")
        self.closeSockets()
        self.communicateWithServer()

    def closeSockets(self):
        self._socketTCP.close()
        self._socketUDP.close()


if __name__ == "__main__":
    client = Client(2062, '127.0.0.1')





