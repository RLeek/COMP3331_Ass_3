import socket	
import sys
import json
import base64
import select
import struct

def shutdown(socket):
  print("Goodbye server shutting down")
  sendMessage(composeMessage(["Command"], ["LEAVE"]), socket)
  socket.close()
  sys.exit()

def inputHandler(socket):
  readable,writable,exceptionavailable = select.select([sys.stdin,socket],[],[])
  for i in readable:
    if (i == sys.stdin):
      command = sys.stdin.readline()
    elif (i == socket):
      print("")
      shutdown(socket)
  return command

def login(socket):
  username = input("Enter username: ")
  username = username.split()[0]
  sendMessage(composeMessage(["Command", "Username"], ["Login", username]), socket)
  reply = recieveMessage(socket)["Message"]
  if (reply == "Account exists"):
    password = input("Enter password: ")
    password = password.split()[0]
    sendMessage(composeMessage(["Command", "Password"], ["Login", password]), socket)
  elif (reply == "New user"):
    password = input("Enter new password for " + username+": ")
    password = password.split()[0]
    sendMessage(composeMessage(["Command", "Password"], ["Login", password]), socket)
  elif(reply == "Account already logged in"):
    print(username + " has already logged in")
    return login(socket)
  reply = recieveMessage(socket)["Message"]
  if (reply == "Successful login"):
    print("Welcome to the forum")
    return username
  elif (reply == "Incorrect password"):
    print("Invalid Password")
    return login(socket)

def recieveMessage(socket):
  size = (struct.unpack("i", socket.recv(struct.calcsize("i"))))[0]
  complete_message = bytearray()
  message_size = 0
  while(message_size < size):
    message = socket.recv(size-message_size)
    complete_message.extend(message)
    message_size = len(complete_message)
  complete_message = json.loads(complete_message.decode("utf-8"))
  if ("status" in complete_message):
    if (complete_message["status"] == "Closing down server"):
      shutdown(socket)
  else:
    return complete_message

def recieveBinaryMessage(socket, size):
  complete_message = bytearray()
  message_size = 0
  while(message_size < size):
    message = socket.recv(size-message_size)
    complete_message.extend(message)
    message_size = len(complete_message)
  return complete_message

def sendMessage(message, socket):
  message = json.dumps(message).encode("utf-8")
  message = struct.pack("i", len(message)) + message
  socket.sendall(message)

def sendBinaryMessage(message, socket):
  socket.sendall((message))

def handleLST(socket, command):
  if (len(command) != 2):
    print("Incorrect syntax for LST")
  else:
    sendMessage(composeMessage(["Command", "Username"], command), socket)
    reply = recieveMessage(socket)
    handleLSTResponse(reply)
 
def handleCRT(socket, command):
  if (len(command) != 3):
    print("Incorrect syntax for CRT")
  else:
    sendMessage(composeMessage(["Command", "ThreadTitle", "Username"], command ), socket)
    reply = recieveMessage(socket)
    handleCRTResponse(reply)

def handleMSG(socket, command):
  if (len(command) < 4):
    print("Incorrect syntax for MSG")
  else:
    sendMessage(composeMessage(["Command", "ThreadTitle","Message", "Username"], [command[0], command[1], " ".join(command[2:-1]), command[-1]]), socket)
    reply = recieveMessage(socket)
    handleMSGResponse(reply)

def handleDLT(socket, command):
  if (len(command) != 4):
    print("Incorrect syntax for DLT")
  elif (not isInt(command[2])):
    print("Incorrect syntax for DLT")
  elif (int(command[2]) < 1):
    print("Incorrect syntax for DLT")
  else:
    sendMessage(composeMessage(["Command", "ThreadTitle","MessageNumber", "Username"], [command[0], command[1], int(command[2])-1, command[-1]]), socket)
    reply = recieveMessage(socket)
    handleDLTResponse(reply)

def handleEDT(socket, command):
  if (len(command) < 5):
    print("Incorrect syntax for EDT")
  elif (not isInt(command[2])):
    print("Incorrect syntax for EDT")
  elif (int(command[2]) < 1):
    print("Incorrect syntax for EDT")
  else:
    sendMessage(composeMessage(["Command", "ThreadTitle","MessageNumber", "Message","Username"], [command[0], command[1], int(command[2])-1, " ".join(command[3:-1]), command[-1]] ), socket)
    reply = recieveMessage(socket)
    handleEDTResponse(reply)

def handleRDT(socket, command):
  if (len(command) != 3):
    print("Incorrect syntax for RDT")
  else:
    sendMessage(composeMessage(["Command", "ThreadTitle", "Username"], command ), socket)
    reply = recieveMessage(socket)
    handleRDTResponse(reply)

def handleUPD(socket, command):
  if (len(command) != 4):
    print("Incorrect syntax for UPD")
  else:
    f = open(command[2], 'rb')
    command.append(len(f.read()))
    f.close()
    sendMessage(composeMessage(["Command", "ThreadTitle", "Filename","Username","Filesize"], command), socket)
    reply = recieveMessage(socket)
    handleUPDResponse(reply, command[2])

def handleDWN(socket, command):
  if (len(command) != 4):
    print("Incorrect syntax for DWN")
  else:
    sendMessage(composeMessage(["Command", "ThreadTitle", "Filename", "Username"], command ), socket)
    reply = recieveMessage(socket)
    handleDWNResponse(reply, socket, command[2])

def handleRMV(socket, command):
  if (len(command) != 3):
    print("Incorrect syntax for RMV")
  else:
    sendMessage(composeMessage(["Command", "ThreadTitle", "Username"], command ), socket)
    reply = recieveMessage(socket)
    handleRMVResponse(reply)

def handleXIT(socket, command):
  if (len(command) != 2):
    print("Incorrect syntax for XIT")
    return False
  else:
    sendMessage(composeMessage(["Command", "Username"], command ), socket)
    reply = recieveMessage(socket)
    return handleXITResponse(reply)

def handleSHT(socket, command):
  if (len(command) != 3):
    print("Incorrect syntax for SHT")
    return False
  else:
    sendMessage(composeMessage(["Command", "adminPassword", "Username"], command ), socket)
    reply = recieveMessage(socket)
    return handleSHTResponse(reply)

def composeMessage(headers, arguments):
  message = {}
  i = 0
  while(i < len(headers)):
    message[headers[i]] = arguments[i]
    i+=1
  return message

def handleLSTResponse(reply):
  threads = reply["Threads"]
  if (len(threads) == 0):
    print("No threads to list")
  else:
    print("The list of active threads: ")
    for i in threads :
      print(i)

def handleCRTResponse(reply):
  if (reply["Status"] == "Error"):
    print(reply["Message"])
  else:
    print("Thread " + reply["ThreadTitle"] + " created")

def handleMSGResponse(reply):
  if (reply["Status"] == "Error"):
    print(reply["Message"])
  else:
    print("Message posted to " + reply["ThreadTitle"])

def handleDLTResponse(reply):
  if (reply["Status"] == "Error"):
    print(reply["Message"])
  else:
    print("Message deleted from " + reply["ThreadTitle"])

def handleEDTResponse(reply):
  if (reply["Status"] == "Error"):
    print(reply["Message"])
  else:
    print("Message edited in " + reply["ThreadTitle"])

def handleRDTResponse(reply):
  if (reply["Status"] == "Error"):
    print(reply["Message"])
  else:
    if (len(reply["ThreadEntries"]) == 0):
      print("Thread " + reply["ThreadTitle"] + " is empty")
    else:
      line = 1
      for i in reply["ThreadEntries"]:
        if (i["Type"] == "Message"):
          print(str(line) + " " + i["User"]+": "+i["Message"])
          line +=1
        elif (i["Type"] == "File"):
          print(i["User"] + " uploaded " + i["Filename"])

def handleUPDResponse(reply, filename):
  if (reply["Status"] == "Error"):
    print(reply["Message"])
  else:
    f = open(filename, 'rb')
    sendBinaryMessage(f.read(), socket)
    reply = recieveMessage(socket)
    print("File uploaded to " + reply["ThreadTitle"])


def handleDWNResponse(reply, socket, filename):
  if (reply["Status"] == "Error"):
    print(reply["Message"])
  else:
    file = recieveBinaryMessage(socket, reply["Filesize"])
    f = open(filename, 'wb+')
    f.write(file)
    print("File " + filename + " downloaded")

def handleRMVResponse(reply):
  if (reply["Status"] == "Error"):
    print(reply["Message"])
  else:
    print("Thread " + reply["ThreadTitle"] + " has been removed")

def handleXITResponse(reply):
  if (reply["Status"] == "Error"):
    print(reply["Message"])
    return False
  else:
    print("Goodbye")
    sendMessage(composeMessage(["Command"], ["LEAVE"]), socket)
    return True

def handleSHTResponse(reply):
  if (reply["Status"] == "Error"):
    print(reply["Message"])
    return False
  else:
    print("Goodbye, Server shutting down")
    sendMessage(composeMessage(["Command"], ["LEAVE"]), socket)
    return True

def isInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False


try:
  server_ip = sys.argv[1]
  server_port = int(sys.argv[2])
except:
  print("Lacking or Incorrect arguments provided")
  sys.exit()

try:
  socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error:
  print ('Failed to create socket')
  sys.exit()

socket.connect((server_ip , server_port))

username = login(socket)

while True: 
  print("Enter one of the following commands: CRT, MSG, DLT, EDT, LST, RDT, UPD, DWN, RMV, XIT, SHT: ", end="", flush=True)
  command = inputHandler(socket)
  command = command.split()
  command.append(username) 
  if (command[0] == "CRT"):
    handleCRT(socket, command)
  elif (command[0] == "LST"):
    handleLST(socket, command)
  elif (command[0] == "MSG"):
    handleMSG(socket, command)
  elif (command[0] == "DLT"): 
    handleDLT(socket, command)
  elif (command[0] == "EDT"):
    handleEDT(socket, command)
  elif (command[0] == "RDT"):
    handleRDT(socket, command)
  elif (command[0] == "UPD"):
    handleUPD(socket, command)
  elif (command[0] == "RMV"):
    handleRMV(socket, command)
  elif (command[0] == "DWN"):
    handleDWN(socket, command)
  elif (command[0] == "XIT"):
    close = handleXIT(socket, command)
    if (close):
      break
  elif (command[0] == "SHT"):
    shutdown = handleSHT(socket, command)
    if (shutdown):
      break
  else:
    print("Invalid command")

