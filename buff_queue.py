
import collections
import os.path


class BuffQueue:
    """Buffer queue class."""

    def __init__(self, **kwargs):
        self._save_dir = kwargs.get("save_dir", ".")
        self._max_entries = kwargs.get('max_entries', 5)
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

    def peek(self, index: int = 0):
        return self._queue[index]

    def is_full(self):
        return self.num_entries >= self.max_entries

    def save(self, file_name: str, index_from: int = 0):
        """
        Save current content of queued buffers in a single file.
        :param file_name: Name of file used to save buffer data.
        :param index_from: Starting buffer index.
        :return:
        """
        file_path = os.path.join(self._save_dir, file_name)
        with open(file_path, "w+") as file:
            for i in range(index_from, self.num_entries):
            #for buff in self._queue[index_from:]:
                #for line in buff.buff:
                for line in self._queue[i].buff:
                    file.write(line + '\n')



