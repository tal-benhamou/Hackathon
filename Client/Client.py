import socket
import struct
import msvcrt
import time
from select import select
class Client():

    def __init__(self, port, ip) -> None:
        self._port = port
        self._ip = ip
        self._teamName = "noName"
        self._socketTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socketUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.communicateWithServer()

    def communicateWithServer(self):
        print("Client started, listening for offer requests...")
        try:
            offer_from_server, ip =  self._socketUDP.recvfrom(1024)
        except:
            return # try again
        print(f"Received offer from {ip},attempting to connect...")
        magic_cookie, type, TCPort = struct.unpack(offer_from_server)
        if (magic_cookie != 0xabcddcba or type != 2): 
            return # try again
        try:
            self._socketTCP.connect((self._ip, TCPort))
        except:
            return # try again
        self.Game()


    def Game(self):
        message = self._teamName + "\n"
        self._socketTCP.sendto(message, self._ip)
        try:
            from_server = self._socketTCP.recv(1024)
        except:
            return
        print(str(from_server))
        start_time = time.time()
        user_input , stam, stam2 = select([msvcrt.getch()], [], [],10)
        if (len(user_input) == 0):
            pass
        else:
            self._socketTCP.sendto(user_input[0],self._ip)
        from_server = self._socketTCP.recv(1024)
        print(str(from_server))
        print("Server disconnected, listening for offer requests...")
        self.communicateWithServer()
        
if __name__ == "__main__":
    client = Client( 2062 , '127.0.0.1')



        

    