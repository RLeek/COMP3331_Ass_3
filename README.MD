
# Program design

## Files 
This program uses  python3  and  supports multiple users . For the server there are 4 associated files exceptions.py, globals.py, serverMethods.py and server.py. The file exceptions.py contains custom exceptions for when commands fail on the server-side. The file globals.py contains global variables that need to be accessed by server.py and serverMethods.py to keep track and communicate between threads. These global variables are ExecutionQueue, clientSockets, admin\_pass, shutdown and currentUsers. ServerMethods.py contains all the functions required for each of the commands, including logging in. The file server.py contain the functions that handle and create threads for concurrency, as well as starting and closing the server.

## System design Overview 

The general system design is structured to support multi-threading, with queues and events. Since each of the commands are treated as being atomic actions, the system was structured as a multiple producer and single consumer problem. Hence, when the server is running, there will always be two threads. 

Main thread:  This will accept new connections and create the associated client threads

Execution thread:  This will act as the single 'consumer' by taking elements out of the executionQueue. These elements will be in the form of a function associated with a command, its arguments and an event object.

There is one additional thread for each client in the form of the client thread: 
Client thread:  This is the 'producer' and will receive commands and then add them to the executionQueue and wait until the executionQueue has consumed this command before receiving extra commands. 

There were several other design considerations for the functions associated with each command. In particular, each command is treated independently, meaning that there is no assumed state or declared variables that persist between commands, other than global variables in globals.py. Furthermore, instead of reading and editing threads at the same time, threads are read once and converted to a different representation, usually a list or dictionary for further changes and then the file is completely erased and written to using this representation. This is preferable as it allows for pure functions when interacting with the content of threads, preventing side-effects and making it easier to test.

The clients design is fairly simple. It uses selects() to determine if there is content to read from either the server or the user at the same time, so it can immediately respond to shutdowns. When the user provides valid commands to the client, a corresponding function handles sending and receiving the request/response before waiting for more commands.

## How the system works 

When a client recieves a command, it will send that command with its relevant entries to the client thread via its socket. The client thread will be reading the socket and recieve this message. It will then add the function associated with the command, its arguments and an event object to the executionQueue. The client will then set the event object to false and wait for the event object to be set true by the execution thread. The execution thread, on detecting that the executionQueue is not empty will then read the queue, obtaining the command, its arguments and an event object. It will then execute the command with its arguments. This will always involves sending a response to the client, which will cause the client to ask the user for more input, after processing this response. The event object is then set to True. This will then cause the corresponding client thread waiting for the event object, to be active again. This client thread will then begin listening to the socket for the next command. This event object is required, because when the execution thread executes a command, this may involve reading or sending from the socket, which cannot be done if the client thread is already listening to the socket. Hence, the event object is used to tell the client thread that it can listen to the socket again, as the execution thread has finished their command. This summarizes how the system works in general.

## Server Commands

Most of the commands follow essentially the same structure noted above with different functionality. Brief details of commands that differ from this structure are explained below: 

The login command uses currentUsers to keep track of logged in users. The currentUser essentially maps thread ids to usernames. Whenever a client logs in, the thread id and their username is added to currentUser and removed when they exit. 

The XIT command is executed immediately instead of being added to the executionQueue. This is because this command does not interact with any files and only requires closing sockets. 

For both UPD and DWN, two messages are sent by the side which is sending the requested file. The first message contains details regarding the file and whether the file is being sent over. The second message contains the actual binary file (assuming no errors)

The SHT command takes several steps to close down the server. First, it sets shutdown to true. This will cause the main thread to terminate. The execution thread will then write to each client, telling them they are to shut down, using the global variable clientSockets. The execution thread will then stop executing methods in its queue, and instead only set the event object to true, repeating this until currentUsers is empty. Each client, on receiving the SHT message will send a message to the server with a special command "LEAVE". Each client thread on receiving this message will then shutdown. The client is used to close their threads because the client thread will be listening to the socket and will not close until they receive a message.

## Application layer message format 

The message format differs between the client and the server in several ways. Both the client and server will always add 4 bytes in front of the message, which indicates the size of the whole message. This ensures that the whole message is received even when it is fragmented whilst being sent. The rest of the message will be in the JSON format. For the messages sent by the client, this JSON message will always contain the "Command" entry to identify the command, with additional entries for the relevant arguments. It will also always contain a "Username" entry, for quick identification for the client thread. E.g. For CRT, the JSON will be {Command: "CRT", ThreadTitle:"title", Username: "user1"} . The server will always respond with a JSON message containing the "Status" entry. "Status" usually takes the value of either "Ok" or "Error". On "Error", this JSON message will always contain a "Message" entry that the client will print before waiting for the next command. On an "Ok", the relevant entries for the previously sent command are provided. E.g. For a successful MSG command the server will send {Status:"OK", ThreadTitle: "title"} . For all unsuccessful commands the server will send {Status: "Error", Message: "Error Message"}. Binary messages are used for sending files and the size of these files are specified by the previously sent message for UPD or DWN through the entry "Filesize", to ensure the whole file is received despite fragmentation.

## Trade-offs 

The main trade-offs made were usually in the form of simplicity. Namely, no commands are processed simultaneously even if they don't affect each other. For example two separate clients reading the same thread will not cause concurrency issues, however in this system they will always be executed one after the other. This is because it is far more simple then allowing concurrency for specific command orders. 

Another trade-off made was for UPD and DWN, where two messages are sent, the first one containing the request/response and the second containing the binary file. This means the file won't be sent when there are errors, saving bandwidth at the cost of slightly more complexity. 

Another trade-off made was more vague error messages. This was largely done to avoid having to case on every kind of failure for each command. For example, when DWN fails the error message will not specify if it is the thread that does not exist or the file that does not exist, only that the specific file could not be found in the thread. 

## Improvements and extensions 

There are several clear ways to improve and extend this server so that it performs better and has additional functionality. One way to improve the server is allowing commands to be executed simultaneously whilst still retaining the correct final state. This can be done through using a database instead of separate files, as databases have built in concurrency control which makes this incredibly easy. Furthermore, databases are an efficient data representation, which will likely be faster when reading large threads. The other improvement that may be desirable is security, through encrypting passwords that are sent by the client. 

There are several extensions that may be useful. Using databases makes extensions such as profiles quite simple as seeing all the comments of a given user would only require joining several tables instead of opening multiple files. It would also allow efficient filtering of threads based on username or message content.
