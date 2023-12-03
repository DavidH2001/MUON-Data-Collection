from abc import ABC, abstractmethod


class DataChannel(ABC):

    def __init__(self):
        super().__init__()

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def write(self):
        pass
