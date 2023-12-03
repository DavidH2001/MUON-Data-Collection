
import collections


class BuffQueue:

    def __init__(self, **kwargs):
        self._max_entries = kwargs.get('max_entries', 7)
        self._queue: collections.deque = collections.deque(maxlen=self._max_entries)
        self._mid_index: int = int(self._max_entries / 2)

    @property
    def mid_index(self):
        return self._mid_index

    @property
    def max_entries(self):
        return self._max_entries

    @property
    def num_entries(self):
        return len(self._queue)

    def append(self, buff):
        self._queue.append(buff)

    def peak(self, index: int = 0):
        return self._queue[index]



