import scapy
from scapy.arch import get_if_addr
import socket
from _thread import start_new_thread
from threading import Thread, Lock
import threading
import struct
import time
import random
# import readchar

CHANNEL_UDP = 13117
MAGIC_COOKIE = 0xabcddcba
TYPE_BROADCAST = 0x2 
KILO_BYTE = 1024


class Server():

    def __init__(self, IP, port, channel) -> None:

        self._port = port
        self._IP = IP
        self._channel = channel

        self._serverAddress = (self._IP, self._port)
        self._socketTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socketTCP.settimeout(10)
        self._socketTCP.bind(self._serverAddress)

        self._socketUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self._numTeamINC = Lock()
        self._StartGame = Lock()
        self._someOneAns = Lock()


        self._Teams = {}
        self._numTeams = 0
        self._result = ""
        self._stopServer = False
        self._finishGame = False

        self._StartGame.acquire()  # for waiting to event in 'startServer()'

        self.startServer()

    def stopServer(self):
        self._stopServer = True

    def startServer(self):
        # starting server with threads
        self._FirstAns = Lock()
        threading.Thread(target=self.Listening_UDP).start()
        threading.Thread(target=self.Listening_TCP).start()

        self._StartGame.acquire() # wait here, then its open - the thread lock it and continue
        self._StartGame.release() # for waiting in the next game
        self.Game()
        self._StartGame.acquire()  # for waiting to event in the next game
        # AFTER GAME FINISHED
        # Closing TCP Connections
        for key, val in self._Teams.items():
            val[1].close()

        print("Game Over, sending out offer requests...")
        self._finishGame = False
        self._Teams.clear()
        self._numTeams = 0
        print("Almost Another Game")

        print("Another Game")
        if (self._stopServer):
            self._socketTCP.close()
            self._socketUDP.close()
            return

        self.startServer()

    def Listening_UDP(self):
        # self._socketUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        print(f"Server started, listening on IP address {self._IP}")
        # opened_UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        packet_to_send = struct.pack(">IbH", MAGIC_COOKIE, TYPE_BROADCAST, self._port)
        print(self._port)
        ip = '.'.join(self._IP.split('.')[:2]) + '.255.255'

        while (self._numTeams != 2):  # true = the game dont start yet
            print("send UDP")
            # print(self._StartGame.locked())
            self._socketUDP.sendto(packet_to_send, (ip, self._channel))
            time.sleep(1)

    def Listening_TCP(self):
        # self._socketTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self._socketTCP.settimeout(10)
        # self._serverAddress = (self._IP, self._port)
        # self._socketTCP.bind(self._serverAddress)

        self._socketTCP.listen()
        while True:
            try:
                print("Listening on TCP")
                connection, client_address = self._socketTCP.accept()  # waiting for client
            except:
                print("exceptServer")
                continue
            self._numTeamINC.acquire()
            self._numTeams += 1
            self._Teams[self._numTeams] = ['', connection, client_address]
            print(f"numTeams = {self._numTeams}")
            if (self._numTeams < 3):
                connection.settimeout(10) # recv will wait 10 sec
                start_new_thread(self.Client_Handle, (connection, client_address, self._numTeams))
            else:
                # connection.sendall()  # rejecting
                break
            self._numTeamINC.release()

            if (self._numTeams == 2):
                print("numTeams = 2 and ListeningTCP thread is die")
                break
        # time.sleep(0.005)

    def Client_Handle(self, connection, client_address, nt):
        # time.sleep(0.5)
        receive_mess = str(connection.recv(KILO_BYTE), 'utf-8')  # name of Team
        print(receive_mess)
        self._Teams[nt][0] = receive_mess[:receive_mess.index("\n")]
        print(f"self._Teams[{nt}] = {self._Teams[nt]}")
        if (nt == 2):
            try:
                self._StartGame.release()
                print("releasing")
            except:
                pass
        print(f"self._Teams[{nt}] = {self._Teams[nt]}")

    def Game(self):  # main thread
        time.sleep(10)
        print("START-GAME")
        problem = self.GeneratingProblem()
        answer = int(problem[0]) + int(problem[2])
        print(f"self._Teams[1][0] = {self._Teams[1][0]} \nself._Teams[2][0] = {self._Teams[2][0]}")
        message = "Welcome to Quick Maths.\nPlayer 1: " + str(self._Teams[1][0]) + \
                  "\nPlayer 2: " + str(self._Teams[2][0]) + "\n==\nPlease answer the following question as" \
                  + " fast as you can:\nHow much is " + ''.join(problem) + "?"

        print("sending message")

        for key, value in self._Teams.items(): # if someone exit in the middle of the game there is error i tried to fix it but its not realistic
            try:
                value[1].sendall(message.encode())
            except ConnectionResetError or ConnectionAbortedError:
                self._numTeams -= 1
                self.startServer()



        self._someOneAns.acquire()

        print("threads go into checkFirst")

        team1 = Thread(target=self.CheckFirst, args=(answer, 1))
        team2 = Thread(target=self.CheckFirst, args=(answer, 2))
        team1.start()
        team2.start()
        self._someOneAns.acquire() # wait here
        self._someOneAns.release() # for NOT waiting in line 151
        print("some one answer")

        print(f"result = {self._result}")

        for key, value in self._Teams.items():
            try:
                value[1].sendall(self._result.encode())
            except:
                continue

        while (team1.is_alive() or team2.is_alive()):
            # print(f"team1.is_alive() = {team1.is_alive()}\nteam2.is_alive() = {team2.is_alive()}")
            continue
        # time.sleep(3)
        # jumping to 'startServer()' and ending the game

    def CheckFirst(self, answer, c):

        start_time = time.time()

        while (time.time() - start_time < 10):
            try:
                print(f"thread of team{c} is waiting in recv")
                answer_Team = str(self._Teams[c][1].recv(KILO_BYTE), 'utf-8')  # maybe need less than 1024
                print(f"thread of team{c} is after recv")
            except ConnectionAbortedError:
                return
            except socket.timeout:
                print("socket timeout")
                break
            except:
                return
            print(f"thread of team{c} is before FirstAns.acquire")
            if (self._finishGame):
                return
            self._FirstAns.acquire()  # critical section
            print(f"thread of team{c} is after FirstAns.acquire")
            if (self._finishGame):
                return
            if (time.time() - start_time >= 10):
                self._result = "Game over!\nThe correct answer was " + str(answer) + "!\n\n" \
                               + "DRAW!!!"
                try:
                    self._someOneAns.release()
                except:
                    pass
                self._finishGame = True
                return
            # print(f"answer of team{c} = {answer_Team}")


            # print("start ifim")
            if ((answer_Team != None) and (not self._finishGame) and answer_Team == answer):
                self._result = "Game over!\nThe correct answer was " + str(answer) + "!\n\n" \
                          + "Congratulations to the winner: " + self._Teams[c][0]
                # print("if1")
                try:
                    self._someOneAns.release()
                except:
                    pass
                self._finishGame = True
                try:
                    self._FirstAns.release()
                except:
                    pass
                return

            elif ((answer_Team != None) and (not self._finishGame) and answer_Team != answer):
                # print("if2")
                if (c == 1):
                    self._result = "Game over!\nThe correct answer was " + str(answer) + "!\n\n" \
                              + "Congratulations to the winner: " + self._Teams[2][0]
                else:
                    self._result = "Game over!\nThe correct answer was " + str(answer) + "!\n\n" \
                              + "Congratulations to the winner: " + self._Teams[1][0]

                try:
                    self._someOneAns.release()
                except:
                    pass
                self._finishGame = True
                try:
                    self._FirstAns.release()
                except:
                    pass
                return

            try:
                self._FirstAns.release()
            except:
                pass
        self._finishGame = True
        try:
            self._someOneAns.release()
        except:
            pass
        if (self._result != ""):
            return
        self._result = "Game over!\nThe correct answer was " + str(answer) + "!\n\n" \
                           + "DRAW!!!\n"


    def GeneratingProblem(self) -> list:
        # operations = ["+"]
        lst = [str(random.randint(1, 4)), "+", str(random.randint(1, 5))]
        return lst


if __name__ == "__main__":
    Server(get_if_addr("eth1"), 2990, CHANNEL_UDP)



