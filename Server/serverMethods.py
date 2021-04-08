import socket as sock
import sys
import os.path
import copy
import json
import glob
import re
import threading
import queue
import exceptions
import globals
import struct

def sendMessage(message, socket):
  message = json.dumps(message).encode("utf-8")
  message = struct.pack("i", len(message)) + message
  socket.sendall(message)

def sendBinaryMessage(message, socket):
  socket.sendall((message))

def recieveMessage(socket):
  size = (struct.unpack("i", socket.recv(struct.calcsize("i"))))[0]
  complete_message = bytearray()
  message_size = 0
  while(message_size < size):
    message = socket.recv(size-message_size)
    complete_message.extend(message)
    message_size = len(complete_message)
  return json.loads(complete_message.decode("utf-8"))

def recieveBinaryMessage(socket, size):
  complete_message = bytearray()
  message_size = 0
  while(message_size < size):
    message = socket.recv(size-message_size)
    complete_message.extend(message)
    message_size = len(complete_message)
  return complete_message

def writeThread(f, thread):
  f.truncate(0)
  f.seek(0)
  f.write(thread["Creator"]+ "\n")
  line = 1
  for i in thread["Entries"]:
    if (i["Type"] == "Message"):
      f.write(str(line) + " " + i["User"]+": "+i["Message"] + "\n")
      line +=1
    elif (i["Type"] == "File"):
      f.write(i["User"] + " uploaded " + i["Filename"]+"\n")
  f.truncate()

def readThread(f):
  f.seek(0)
  thread = {}
  thread["Entries"] = []
  i2 = 0
  for i in f:
    if (i2 == 0):
      thread["Creator"] = i.strip("\n")
    else:
      i.strip("\n")
      i = i.split()
      if (i[1] == "uploaded"):
        thread["Entries"].append({"Type":"File","User": i[0], "Filename":i[2]})
      else:
        thread["Entries"].append({"Type":"Message", "User":i[1][:-1], "Message":" ".join(i[2:])})
    i2+=1
  return thread

def findThreads():
  files = glob.glob("*")
  i = 0
  while(i < len(files)):
    if (files[i] in ["__pycache__", "credentials.txt", "exceptions.py", "globals.py", "server.py", "serverMethods.py"]):
      files.remove(files[i])
    elif("-" in files[i]):
      files.remove(files[i])
    else:
      i +=1
  return files

def readCredentials(f):
  f.seek(0)
  credentials = []
  for line in f:
    line = line.split()
    if (len(line) == 2):
      username, password = line
      credentials.append({"Username": username, "Password":password})
  return credentials

def writeCredentials(f, credentials):
  f.truncate(0)
  f.seek(0)
  for i in credentials:
    f.write(i["Username"] + " " + i["Password"] + "\n")
  f.truncate()

def authenticate(client, threadId): 
  f = open("credentials.txt", 'a+')
  credentials = readCredentials(f)
  while(True):
    f.seek(0)
    received_username = recieveMessage(client)["Username"]
    if (loggedin(received_username)):
      sendMessage(composeMessage(["Status", "Message"], ["Error", "Account already logged in"]), client)
      continue
    password = findCredentials(credentials, received_username)
    if (password != None):
      sendMessage(composeMessage(["Status", "Message"], ["Ok", "Account exists"]), client)
      received_password = recieveMessage(client)["Password"]
      if (password == received_password):
        sendMessage(composeMessage(["Status", "Message"], ["Ok", "Successful login"]), client)
        print(received_username + " successful login")
        globals.currentUsers[threadId] = received_username
        f.close()
        return
      else:
        sendMessage(composeMessage(["Status", "Message"], ["Error", "Incorrect password"]), client)
        print("Incorrect password")
    else:
      sendMessage(composeMessage(["Status", "Message"], ["Ok", "New user"]), client)
      print("New account")
      received_password = recieveMessage(client)["Password"]
      credentials = addCredentials(credentials, received_username, received_password)
      writeCredentials(f, credentials)
      sendMessage(composeMessage(["Status", "Message"], ["Ok", "Successful login"]), client)
      print(received_username + " successful login")
      globals.currentUsers[threadId] = received_username
      f.close()
      return

def handleCRT(client, message):
  print(message["Username"] + " issued CRT command")
  if (os.path.isfile(message["ThreadTitle"]) == False):
    f = open(message["ThreadTitle"], 'w+')
    writeThread(f, createThread(message["Username"]))
    f.close()
    print("Thread " + message["ThreadTitle"] + " created")
    sendMessage(composeMessage(["Status", "ThreadTitle"],["OK", message["ThreadTitle"]]), client)
  else:
    errorMessage = "Thread " + message["ThreadTitle"] + " exists"
    print(errorMessage)
    sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)

def handleLST(client, message):
  print(message["Username"] + " issued LST command")
  threads = findThreads()
  sendMessage(composeMessage(["Status", "Threads"],["OK", threads]), client)

def handleMSG(client, message):
  print(message["Username"] + " issued MSG command")
  try:
    if (message["ThreadTitle"] in ["__pycache__", "credentials.txt", "exceptions.py", "globals.py", "server.py", "serverMethods.py"]):
      raise exceptions.AuthorityError("Incorrect permissions")
    f = open(message["ThreadTitle"], 'r+')
    thread = readThread(f)
    thread = addThreadEntry(thread, message["Username"], message["Message"])
    writeThread(f, thread)
    print("Message posted to " + message["ThreadTitle"] + " thread")
    f.close()
    sendMessage(composeMessage(["Status", "ThreadTitle"],["OK", message["ThreadTitle"]]), client)
  except OSError:
    errorMessage = "Thread " + message["ThreadTitle"] + " does not exist"
    print(errorMessage)
    sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)
  except exceptions.AuthorityError as e:
    errorMessage = e.message
    print(errorMessage)
    sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)

def handleDLT(client, message):
  print(message["Username"] + " issued DLT command")
  try:
    if (message["ThreadTitle"] in ["__pycache__", "credentials.txt", "exceptions.py", "globals.py", "server.py", "serverMethods.py"]):
      raise exceptions.AuthorityError("Incorrect permissions")
    f = open(message["ThreadTitle"], 'r+')
    thread = readThread(f)
    thread = deleteThreadEntry(thread, message["Username"], message["MessageNumber"])
    writeThread(f, thread)
    print("Message has been deleted")
    f.close()
    sendMessage(composeMessage(["Status", "ThreadTitle", "MessageNumber"],["OK", message["ThreadTitle"], message["MessageNumber"]]), client)
  except OSError:
    errorMessage = "Thread " + message["ThreadTitle"] + " does not exist"
    print(errorMessage)
    sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)
  except exceptions.AuthorityError as e:
    errorMessage = e.message
    print(errorMessage)
    sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)

def handleEDT(client, message):
  print(message["Username"] + " issued EDT command")
  try:
    if (message["ThreadTitle"] in ["__pycache__", "credentials.txt", "exceptions.py", "globals.py", "server.py", "serverMethods.py"]):
      raise exceptions.AuthorityError("Incorrect permissions")
    f = open(message["ThreadTitle"], 'r+')
    thread = readThread(f)
    thread = updateThreadEntry(thread, message["Username"], message["MessageNumber"], message["Message"])
    writeThread(f, thread)
    print(message["Username"] + " updated message " + str(message["MessageNumber"]) + " in thread")
    f.close()
    sendMessage(composeMessage(["Status", "ThreadTitle", "MessageNumber"],["OK", message["ThreadTitle"], message["MessageNumber"]]), client)
  except OSError:
    errorMessage = "Thread " + message["ThreadTitle"] + " does not exist"
    print(errorMessage)
    sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)
  except exceptions.AuthorityError as e:
    errorMessage = e.message
    print(errorMessage)
    sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)

def handleRDT(client, message):
  print(message["Username"] + " issued RDT command")
  try:
    if (message["ThreadTitle"] in ["__pycache__", "credentials.txt", "exceptions.py", "globals.py", "server.py", "serverMethods.py"]):
      raise exceptions.AuthorityError("Incorrect permissions")
    f = open(message["ThreadTitle"], 'r+')
    thread = readThread(f)
    print("Thread "+message["ThreadTitle"]+" read")
    f.close()
    sendMessage(composeMessage(["Status", "ThreadTitle", "ThreadEntries"],["OK", message["ThreadTitle"],thread["Entries"]]), client)
  except OSError:
    errorMessage = "Thread " + message["ThreadTitle"] + " does not exist"
    print(errorMessage)
    sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)
  except exceptions.AuthorityError as e:
    errorMessage = e.message
    print(errorMessage)
    sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)

def handleUPD(client, message):
  print(message["Username"] + " issued UPD command")
  try:
    if (message["ThreadTitle"] in ["__pycache__", "credentials.txt", "exceptions.py", "globals.py", "server.py", "serverMethods.py"]):
      raise exceptions.AuthorityError("Incorrect permissions")
    f = open(message["ThreadTitle"], 'r+')
    thread = readThread(f)
    thread = addFileEntry(thread, message["Username"], message["Filename"])
    writeThread(f, thread)
    f.close()
    sendMessage(composeMessage(["Status"],["OK"]), client)
    UPDFile = recieveBinaryMessage(client, message["Filesize"])
    f = open(message["ThreadTitle"]+"-"+message["Filename"], 'wb+')
    f.write(UPDFile)
    f.close()
    print(message["Username"] + " Uploaded file " + message["Filename"]  + " to " + message["ThreadTitle"] + " thread")
    sendMessage(composeMessage(["Status", "ThreadTitle", "Filename"],["OK", message["ThreadTitle"], message["Filename"]]), client)
  except OSError:
    errorMessage = "Thread " + message["ThreadTitle"] + " does not exist"
    print(errorMessage)
    sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)
  except exceptions.AuthorityError as e:
    errorMessage = e.message
    print(errorMessage)
    sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)

def handleDWN(client, message):
  print(message["Username"] + " issued DWN command")
  try:
    if (os.path.isfile(message["ThreadTitle"]) == False):
      raise OSError
    f = open(message["ThreadTitle"]+"-"+message["Filename"], 'rb')
    sendMessage(composeMessage(["Status","Filesize"],["OK", len(f.read())]), client)
    print(message["Filename"]+" downloaded from Thread " + message["ThreadTitle"])
    f.seek(0)
    sendBinaryMessage(f.read(), client)
  except OSError as e:
    if (e.filename == message["ThreadTitle"]):
      errorMessage = "Thread" + message["ThreadTitle"] + " does not exist"
      print(errorMessage)
      sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)
    else:
      errorMessage = "File " + message["Filename"] + " does not exist in thread " + message["ThreadTitle"]
      print(errorMessage)
      sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)

def handleRMV(client, message):
  print(message["Username"] + " issued RMV command")
  try:
    if (message["ThreadTitle"] in ["__pycache__", "credentials.txt", "exceptions.py", "globals.py", "server.py", "serverMethods.py"]):
      raise exceptions.AuthorityError("Incorrect permissions")
    f = open(message["ThreadTitle"], 'r')
    thread = readThread(f)
    f.close()
    if (thread["Creator"] != message["Username"]):
      raise exceptions.AuthorityError("The file belongs to another user and cannot be deleted")
    for i in thread["Entries"]:
      if (i["Type"] == "File"):
        os.remove(message["ThreadTitle"]+ "-"+i["Filename"])
    os.remove(message["ThreadTitle"])
    print("Thread " + message["ThreadTitle"] + " removed")
    sendMessage(composeMessage(["Status", "ThreadTitle"],["OK", message["ThreadTitle"]]), client)
  except OSError:
    errorMessage = "Thread " + message["ThreadTitle"] + " does not exist"
    print(errorMessage)
    sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)
  except exceptions.AuthorityError as e:
    errorMessage = e.message
    print(errorMessage)
    sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)

def handleXIT(client, message, threadId):
  print(message["Username"] + " exited")
  sendMessage(composeMessage(["Status"],["OK"]), client)
  for socket in globals.clientSockets:
    if (socket is client):
      socket.close()
      globals.clientSockets.remove(socket)
      break
  globals.currentUsers.pop(threadId)

def handleSHT(client, message):
  print(message["Username"] + " issued SHT command")
  try:
    if (message["adminPassword"] == globals.admin_pass):

      files = glob.glob("*")
      for i in files:
        if (i not in ["exceptions.py", "globals.py", "server.py", "serverMethods.py", "__pycache__"]):
          os.remove(i)
      print("Server shutting down")
      globals.shutDown = True
      for socket in globals.clientSockets:
        try:
          sendMessage(composeMessage(["Status"],["Closing down server"]), socket)
        except:
          continue
    else:
      raise exceptions.AuthorityError("Password is incorrect")
  except exceptions.AuthorityError as e:
    errorMessage = e.message
    print(errorMessage)
    sendMessage(composeMessage(["Status", "Message"],["Error", errorMessage]), client)
    


def loggedin(username):
  for threadId, loggedUser in globals.currentUsers.items():
    if (loggedUser == username):
      return True
  return False

def composeMessage(headers, arguments):
  message = {}
  i = 0
  while(i < len(headers)):
    message[headers[i]] = arguments[i]
    i+=1
  return message

def updateThreadEntry(thread, username, messageNum, message):
  entry = 0
  for idx, i in enumerate(thread["Entries"]):
    if (i["Type"] == "Message"):
      if (entry == messageNum):
        if (i["User"] == username):
          threadCopy = copy.deepcopy(thread)
          threadCopy["Entries"][idx]["Message"] = message
          return threadCopy
        else:
          raise exceptions.AuthorityError("The message belongs to another user and cannot be edited")
      entry +=1
  raise exceptions.AuthorityError("The message number has no corresponding message")

def deleteThreadEntry(thread, username, messageNum):
  entry = 0
  for idx, i in enumerate(thread["Entries"]):
    if (i["Type"] == "Message"):
      if (entry == messageNum):
        if (i["User"] == username):
          threadCopy = copy.deepcopy(thread)
          threadCopy["Entries"].pop(idx)
          return threadCopy
        else:
          raise exceptions.AuthorityError("The message belongs to another user and cannot be edited")
      entry +=1
  raise exceptions.AuthorityError("The message number has no corresponding message")

def addThreadEntry(thread, username, message):
  threadCopy = copy.deepcopy(thread)
  threadCopy["Entries"].append({"Type":"Message","User":username,"Message":message })
  return threadCopy

def createThread(username):
  thread = {}
  thread["Creator"] = username
  thread["Entries"] = []
  return thread

def addFileEntry(thread, username, filename):
  threadCopy = copy.deepcopy(thread)
  threadCopy["Entries"].append({"Type":"File","User":username, "Filename": filename})
  return threadCopy


def findCredentials(credentials, username):
  for i in credentials:
    if (i["Username"] == username):
      return i["Password"]
  return None

def addCredentials(credentials, username, password):
  credentialsCopy = copy.deepcopy(credentials)
  credentialsCopy.append({"Username": username, "Password":password})
  return credentialsCopy
