import socket
import struct
import sys
import scapy
from scapy.arch import get_if_addr
import getch
import keyboard
import time
import random
from select import select
import colorama
from colorama import Fore, Style, Back
import pickle
import json

CHANNEL_UDP = 13117
MAGIC_COOKIE = 0xabcddcba
TYPE_BROADCAST = 0x2 
KILO_BYTE = 1024
TIME_OUT_LENGTH = 10


class Client():

    def __init__(self, ip, teamName) -> None:
        self._ip = ip
        self._teamName = teamName
        self.communicateWithServer()

        
    def communicateWithServer(self):
        '''
        open TCP socket and UDP socket with reused and broadcast,
        UDP socket recieve offer requests from server and check the offer,
        connect with TCP connection to the server and starting the game.
        '''
        self.bonusPrint("Client started, listening for offer requests...")
        self._socketTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socketUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        ip2 = '.'.join(self._ip.split('.')[:2]) + '.255.255'
        self._socketUDP.bind((ip2, CHANNEL_UDP))  # dont change

        while True:
            try:
                offer_from_server, ip = self._socketUDP.recvfrom(KILO_BYTE)
            except:
                continue  # try again
            self.bonusPrint("Receive offer from " +str(ip)+ ", attempting to connect...")

            magic_cookie, types, TCPort = struct.unpack(">IbH", offer_from_server)
            if (magic_cookie != MAGIC_COOKIE or types != TYPE_BROADCAST):
                continue  # try again
            break
        while True:
            try:
                self._socketTCP.connect((ip[0], TCPort))
                break
            except:
                self.bonusPrint("exceptClient")
                continue  # try again
        self.Game()

  
    def Game(self):
        '''
        recieve the game over TCP connection and print, sending answer over TCP connection
        recieve the result of the game over TCP connection, and print.
        '''
        message = self._teamName + "\n"
        self._socketTCP.send(bytes(message, encoding='utf-8'))
        from_server = str(self._socketTCP.recv(KILO_BYTE), 'utf-8')
        self.bonusPrint(from_server)

        user_input, a, b = select([sys.stdin, self._socketTCP], [], [], TIME_OUT_LENGTH)

        if user_input and type(user_input[0]) != type(self._socketTCP):
            user_input = sys.stdin.readline()[:-1]
            if len(user_input) != 0:
                self._socketTCP.send(bytes(str(user_input), encoding='utf-8'))
            else:
                self._socketTCP.send(bytes("None", encoding='utf-8'))
        try:
            from_server = str(self._socketTCP.recv(KILO_BYTE), 'utf-8')
        except:
            self.bonusPrint("TIMEOUT")

        self.bonusPrint(from_server)

        # receive statistics from server
        try:
            stat_from_server = str(self._socketTCP.recv(KILO_BYTE), 'utf-8')
            self.bonusPrint(stat_from_server)
        except:
            self.bonusPrint("stat from server dosent reviced")

        
        self.bonusPrint("Server disconnected, listening for offer requests...")
        self.closeSockets()
        self.communicateWithServer()

    def closeSockets(self):
        self._socketTCP.close()
        self._socketUDP.close()

    def bonusPrint(self, text):
        notGood = ['BLACK', 'WHITE']
        style = vars(colorama.Fore)
        randomColors = [style[c] for c in style if c not in notGood]
        _color = random.choice(randomColors)
        print(''.join([_color + word for word in text]))
    

if __name__ == "__main__":
    Client(get_if_addr("eth1"), "Curdians")





