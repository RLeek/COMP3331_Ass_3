import queue

executionQueue = queue.Queue(maxsize=10)
clientSockets = []
admin_pass = None
shutDown = False
currentUsers = {}