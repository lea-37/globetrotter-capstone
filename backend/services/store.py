"""
Design pattern: SINGLETON
----------------------------------
One JSONStore instance per data file is kept alive for the whole process
(see the _instances cache below). Every repository asks JSONStore.instance(path)
for the same object instead of opening the file itself, so all reads/writes for
a given JSON file go through one guarded gateway — no two parts of the app can
disagree about what's on disk, and file locking only has to be implemented once.
"""
import json
import os
import threading


class JSONStore:
    _instances = {}
    _registry_lock = threading.Lock()

    def __init__(self, path):
        self.path = path
        self._file_lock = threading.Lock()
        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump([], f)

    @classmethod
    def instance(cls, path):
        """Return the single JSONStore for this path, creating it on first use."""
        with cls._registry_lock:
            if path not in cls._instances:
                cls._instances[path] = cls(path)
            return cls._instances[path]

    def read(self):
        with self._file_lock:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)

    def write(self, data):
        with self._file_lock:
            tmp_path = self.path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self.path)

    def next_id(self, data):
        return (max((row.get("id", 0) for row in data), default=0) + 1)
