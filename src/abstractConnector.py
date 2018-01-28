from abc import ABC, abstractmethod


class abstractConnector(ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def readLibrary(self):
        pass

    @abstractmethod
    def backupLibrary(self):
        pass