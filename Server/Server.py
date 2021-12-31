import scapy
from scapy.arch import get_if_addr
import socket
from _thread import start_new_thread
from threading import Thread, Lock, Event
import threading
import struct
import time
import random
import sys
from select import select
import colorama
from colorama import Fore, Style

CHANNEL_UDP = 13117
MAGIC_COOKIE = 0xabcddcba
TYPE_BROADCAST = 0x2 
KILO_BYTE = 1024
SELECT_TIMEOUT = 0.5
TENSEC = 10

class Server():

    def __init__(self, IP, port, channel) -> None:

        self._port = port
        self._IP = IP
        self._channel = channel

        self._serverAddress = (self._IP, self._port)
        self._socketTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socketTCP.bind(self._serverAddress)
        self._socketTCP.listen()

        self._socketUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socketUDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self._numTeamINC = Lock()
        self._FirstAns = Lock()

        self._event = Event()
        self._eventUDP = Event()
        self._startGame = Event()

        self._Teams = {}
        self._numTeams = 0
        self._result = ""
        self._stopServer = False
        self._finishGame = False

        self.startServer()

    def stopServer(self):
        self._stopServer = True

    def startServer(self):
        '''
		starting the server, open two new threads for TCP and UDP.
	    '''
        threading.Thread(target=self.Listening_UDP).start()
        threading.Thread(target=self.Listening_TCP).start()
        self.startNewGame()


    def startNewGame(self): 
        '''
		start new game, after game is finished we call to clear function 
        to reset all the event/parametrs/locks we need.
	    '''      
        self._startGame.wait()
        self.Game()
        self.clear()
    
    def clear(self):
        '''
		reset all the event/parametrs/locks we need.
	    '''
        for key, val in self._Teams.items():
            val[1].close()

        self.bonusPrint("Game Over, sending out offer requests...")
        
        self._event.clear()
        self._startGame.clear()
        self._finishGame = False
        self._Teams.clear()
        self._numTeams = 0
        self._FirstAns = Lock()
        self._eventUDP.set()
        self._eventUDP.clear()
        self.startNewGame()

    def Listening_UDP(self):
        '''
		create communication with UDP, and send the packet.
		if the game not started we send “offer” announcements
        via UDP broadcast once every second.
	    '''

        self.bonusPrint("Server started, listening on IP address " + self._IP)
        packet_to_send = struct.pack(">IbH", MAGIC_COOKIE, TYPE_BROADCAST, self._port)
        ip = '.'.join(self._IP.split('.')[:2]) + '.255.255'

        while (True): 
            self._socketUDP.sendto(packet_to_send, (ip, self._channel))
            time.sleep(1)
            if self._numTeams == 2:
                self._eventUDP.wait()


    def Listening_TCP(self):
        '''
            collect 2 clients over TCP connection
        '''
        while True:
            try:
                connection, client_address = self._socketTCP.accept()  # waiting for client
            except:
                self.bonusPrint("exceptServer")
                continue
            self._numTeamINC.acquire()
            self._numTeams += 1
            self._Teams[self._numTeams] = ['', connection, client_address]
            if (self._numTeams < 3):
                start_new_thread(self.Client_Handle, (connection, client_address, self._numTeams))
            else:
                self.reject(connection)


    def reject(self, c):
        c.send("rejecting")

    def Client_Handle(self, connection, client_address, nt):
        '''
		get from the each client, 
        the message as name of his team.
	    '''

        receive_mess = str(connection.recv(KILO_BYTE), 'utf-8')  # name of Team
        self._Teams[nt][0] = receive_mess[:receive_mess.index("\n")]
        if (nt == 2):
            try:
                self._startGame.set()
            except:
                pass
        self._numTeamINC.release()


    def Game(self):  # main thread
        '''
            waiting 10 sec, generating a math problem, sending the prob over TCP connection,
            sending 2 thread to CheckFirst for recieve the answer of the clients,
            sending the result of the Game and jumping to start another game.
        '''
        time.sleep(TENSEC)
        problem = self.GeneratingProblem()
        answer = int(problem[0]) + int(problem[2])
        message = "Welcome to Quick Maths.\nPlayer 1: " + str(self._Teams[1][0]) + \
                  "\nPlayer 2: " + str(self._Teams[2][0]) + "\n==\nPlease answer the following question as" \
                  + " fast as you can:\nHow much is " + ''.join(problem) + "?"

        for key, value in self._Teams.items(): # if someone exit in the middle of the game there is error i tried to fix it but its not realistic
            try:
                value[1].sendall(message.encode())
            except ConnectionResetError or ConnectionAbortedError:
                self.bonusPrint("connection lost")
                self._numTeams -= 1
                self.startNewGame()

        team1 = Thread(target=self.CheckFirst, args=(answer, self._Teams[1][1], 1))
        team2 = Thread(target=self.CheckFirst, args=(answer, self._Teams[2][1], 2))
        team1.start()
        team2.start()
        self._event.wait()

        for key, value in self._Teams.items():
            try:
                value[1].sendall(self._result.encode())
            except:
                continue

        team1.join()
        team2.join()

    def CheckFirst(self, answer, connection, numteam):
        '''
		parametrs:
			answer - the correct answer of the Generating Problem.
			connection - the connection.
			numteam - number of the team.
		This function is to determine who of the teams answer the question first.
		This function print the winner.
	    '''
        start_time = time.time()
       
        while time.time() - start_time < TENSEC:

            answer_Team, a, b = select([connection], [], [], SELECT_TIMEOUT)
            if answer_Team:
                answer_Team = str(connection.recv(KILO_BYTE), 'utf-8')
            elif not self._finishGame:
                continue
            
            self._FirstAns.acquire() # cs

            if ((not self._finishGame) and answer_Team == answer):

                self._result = "Game over!\nThe correct answer was " + str(answer) + "!\n\n" \
                        + "Congratulations to the winner: " + self._Teams[numteam][0]

                self._event.set()
                self._finishGame = True
                try:
                    self._FirstAns.release()
                except:
                    pass
                return

            elif ((not self._finishGame) and answer_Team != answer):

                if (numteam == 1):
                    self._result = "Game over!\nThe correct answer was " + str(answer) + "!\n\n" \
                            + "Congratulations to the winner: " + self._Teams[2][0]
                else:
                    self._result = "Game over!\nThe correct answer was " + str(answer) + "!\n\n" \
                            + "Congratulations to the winner: " + self._Teams[1][0]

                self._finishGame = True
                self._event.set()
                try:
                    self._FirstAns.release()
                except:
                    pass
                return

            if self._finishGame:
                return
            self._event.set()
            try:
                self._FirstAns.release()
            except:
                pass
            

        # after while = no one answer 
        if not self._finishGame:
            self._result = "Game over!\nThe correct answer was " + str(answer) + "!\n\n" \
                            + "DRAW!!!"
            self._finishGame = True
            try:
                self._FirstAns.release()
            except:
                pass

            self._event.set()
            return

    def GeneratingProblem(self) -> list:
        lst = [str(random.randint(1, 4)), "+", str(random.randint(1, 5))]
        return lst

    def bonusPrint(self, text):
        notGood = ['BLACK']
        style = vars(colorama.Fore)
        randomColors = [style[c] for c in style if c not in notGood]
        _color = random.choice(randomColors)
        print(''.join([_color + word for word in text]))


if __name__ == "__main__":
    Server(get_if_addr("eth1"), 2062, CHANNEL_UDP)



