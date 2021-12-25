# from scapy import scapy
import socket
from _thread import start_new_thread
from threading import Thread, Lock 
import threading
import struct
import time
import random

class Server():
    
    def __init__(self, IP, port, channel ) -> None:
        self._port = port
        self._IP = IP
        self._channel = channel
        self._socketTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socketTCP.settimeout(1)
        self._socketUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._serverAddress = ('', self._port)
        self._socketTCP.bind(self._serverAddress)
        self._Mutex = Lock()
        self._Teams = {}
        self._numTeams = 0
        self._StartGame = Lock()
        self._StartGame.acquire() # for waiting to event in 'startTCP()'
        self._stopServer = False
        self._FirstAns = Lock()
        self._finishGame = False

        self.startTCP()

    def stopServer(self):
        self._stopServer = True

    def startTCP(self):
        # starting server with thread
        Thread(target= self.Listening_UDP()).start()
        Thread(target = self.Listening_TCP()).start()
        self._StartGame.acquire() 
        self.Game()
        # AFTER GAME FINISHED 
        # Closing TCP Connections
        for key, val in self._Teams.items():
            val[1].close()
        
        print("Game Over, sending out offer requests...")
        self._finishGame = False
        self._Teams.clear()
        self._numTeams = 0
        self._StartGame.acquire()  # for waiting to event in the next game

        if (self._stopServer):
            self._socketTCP.close()
            self._socketUDP.close()
            return

        self.startTCP()


    def Listening_UDP(self):
        print(f"Server started, listening on IP address {self._IP}")
    #opened_UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        packet_to_send = struct.pack(">IbH",0xabcddcba, 0x2, self._port)
        
        while (self._StartGame.locked()): # true = the game dont start yet
            self._socketUDP.sendto(packet_to_send,("localhost", self._channel))
            time.sleep(1)
            



    def Listening_TCP(self):
        self._socketTCP.listen(1)
        while True:
            connection, client_address = self._socketTCP.accept() # waiting for client
            self._Mutex.acquire()
            self._numTeams += 1
            self._Mutex.release()
            if (self._numTeams < 3):
                start_new_thread(self.Client_Handle, (connection, client_address))
            else:
                connection.sendall() # rejecting
                break
            

        # Game כרגע רק כאשר הלקוח השלישי מבקש כניסה הוא מקבל דחייה ומתחיל המשחק - לא טוב
       # self.Game()   


    def Client_Handle(self, connection, client_address):
        
        receive_mess = connection.recv(1024) # name of Team
        self._Teams[self._numTeams] = (receive_mess[:receive_mess.index("\n")], connection, client_address)
        if (self._numTeams == 2):
            self._StartGame.release()


        

    
    def Game(self):
        time.sleep(10)
        problem = self.GeneratingProblem()
        answer = int(problem[0])+int(problem[2])
        
        message = "Welcome to Quick Maths.\nPlayer 1: " + str(self._Teams[1][0]) + \
            "\nPlayer 2: " + str(self._Teams[2][0]) +"\n==\nPlease answer the following question as" \
            + " fast as you can:\nHow much is " + ''.join(problem) + "?"
        for key, value in self._Teams.items():
            value[1].sendall(message.encode())
        
        l = Lock()
        l.acquire()
        team1 = Thread(traget= self.CheckFirst(), args=(answer, 1, l))
        team2 = Thread(target=self.CheckFirst(), args=(answer, 2, l))
        team1.start()
        team2.start()
        l.acquire()
        time.sleep(0.001)
        for key, value in self._Teams.items():
            if (not team1 and team2 != "draw"):
                value[1].sendall(team1.encode())
            elif (not team2 and team1 != "draw"):
                value[1].sendall(team2.encode())
            else:
                summary = "Game over!\nThe correct answer was " +str(answer)+ "!\n\n" \
                    + "DRAW!!!"
                value[1].sendall(summary.encode())

        # jumping to 'startTCP()' and ending the game

    def CheckFirst(self, answer, c, lock) -> str:
        start_time = time.time()
        summary = ''
        while (time.time() - start_time < 10):      
            answer_Team = self._Teams[c][1].recv(1024,) # maybe need less than 1024
            self._FirstAns.acquire()
            if (not answer_Team and not self._finishGame and answer_Team==answer):
                summary = "Game over!\nThe correct answer was " +str(answer)+ "!\n\n" \
                    + "Congratulations to the winner: " +self._Teams[c][0]
                lock.release()
                self._finishGame = True
                self._FirstAns.release()
                return summary
            elif (not answer_Team and not self._finishGame and answer_Team!=answer): 
                if (c==1):
                    summary = "Game over!\nThe correct answer was " +str(answer)+ "!\n\n" \
                        + "Congratulations to the winner: " +self._Teams[2][0]
                else:
                    summary = "Game over!\nThe correct answer was " +str(answer)+ "!\n\n" \
                        + "Congratulations to the winner: " +self._Teams[1][0]
                lock.release()
                self._finishGame = True
                self._FirstAns.release()
                return summary
            self._FirstAns.release()
        try:
            lock.release()
        except:
            pass
        return "draw"



    def GeneratingProblem(self) -> str:
        # operations = ["+"]
        lst = [str(random.randint(1,4)),"+", str(random.randint(1,5))]
        return lst

if __name__ == "__main__":
    Server ("127.0.0.1", 2062, 2062)

    

