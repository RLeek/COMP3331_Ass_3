

class Error(Exception):
    pass

class AuthorityError(Error):
    def __init__(self, message):
        self.message = message

class FileError(Error):
    def __init__(self, message):
        self.message = message