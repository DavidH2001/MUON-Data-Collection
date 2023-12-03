
# Add Buff as abstract base class and inherit here?

class TextBuff:

    def __init__(self, **kwargs):
        self._max_entries = kwargs.get('max_entries', 7)
        self._buff = []

    @property
    def buff(self):
        return self._buff

    @property
    def num_entries(self):
        return len(self._buff)

    def append(self, entry: str, reset: bool = False):
        if reset:
            self._buff.clear()
        self._buff.append(entry)


