from abc import ABC, abstractmethod


class abstractBackend(ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def backup(self, file):
        pass
