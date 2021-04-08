import socket
import sys
import json
import threading
import queue
import serverMethods
import globals
import select

#Client thread
def clientHandler(socket):
  event = threading.Event()
  event.clear()
  globals.executionQueue.put([serverMethods.authenticate, socket, threading.current_thread().ident, event])
  while (not globals.shutDown):
    event.wait()
    message = serverMethods.recieveMessage(socket)
    event.clear()
    if (message["Command"] == "CRT"):
      globals.executionQueue.put([serverMethods.handleCRT, socket, message, event])
    elif (message["Command"] == "MSG"):
      globals.executionQueue.put([serverMethods.handleMSG, socket, message, event])
    elif (message["Command"] == "DLT"):
      globals.executionQueue.put([serverMethods.handleDLT, socket, message, event])
    elif (message["Command"] == "EDT"):
      globals.executionQueue.put([serverMethods.handleEDT, socket, message, event])
    elif (message["Command"] == "LST"):
      globals.executionQueue.put([serverMethods.handleLST, socket, message, event])
    elif (message["Command"] == "RDT"):
      globals.executionQueue.put([serverMethods.handleRDT, socket, message, event])
    elif (message["Command"] == "UPD"):
      globals.executionQueue.put([serverMethods.handleUPD, socket, message, event])
    elif (message["Command"] == "DWN"):
      globals.executionQueue.put([serverMethods.handleDWN, socket, message, event])
    elif (message["Command"] == "RMV"):
      globals.executionQueue.put([serverMethods.handleRMV, socket, message, event])
    elif (message["Command"] == "XIT"):
      serverMethods.handleXIT(socket, message, threading.current_thread().ident)
      return
    elif (message["Command"] == "SHT"):
      globals.executionQueue.put([serverMethods.handleSHT, socket, message, event])
  globals.currentUsers.pop(threading.current_thread().ident)


#Execution thread
def executionHandler():
  while (True):
    if (globals.shutDown):
      while(len(globals.currentUsers) != 0):
        if (not globals.executionQueue.empty()):
          items = globals.executionQueue.get()
          event = items[-1]
          event.set()
      return
    if (not globals.executionQueue.empty()):
        items = globals.executionQueue.get()
        func = items[0]
        args = items[1:-1]
        event = items[-1]
        func(*args)
        event.set()

def startClientThread(client):
  clientThread = threading.Thread(target=clientHandler, args=(client,))
  clientThread.start()
  globals.clientSockets.append(client)

def startExecutionThread():
  executionThread = threading.Thread(target=executionHandler)
  executionThread.start()

#Main thread
try:
  server_port = int(sys.argv[1])
  globals.admin_pass = sys.argv[2]
except:
  print("Lacking or Incorrect arguments provided")
  sys.exit()

welcome_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
  welcome_socket.bind(("127.0.0.1", server_port))
except socket.error as msg: 
  print ("Bind failed. Error: "+ str(msg))
  sys.exit()

welcome_socket.listen(10)

startExecutionThread()

print("Waiting for clients")

while (not globals.shutDown):
  readable,writable,exceptionavailable = select.select([welcome_socket],[],[], 0)
  if (readable):
    client, address = welcome_socket.accept()
    print("Client connected")
    startClientThread(client)

welcome_socket.close()


