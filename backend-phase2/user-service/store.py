import json, os, threading

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
