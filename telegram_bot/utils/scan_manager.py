import time
import threading

class ScanManager:
    def __init__(self, ttl=3600):
        self._active_scans = 0
        self._results = {}
        self._ttl = ttl
        self._lock = threading.Lock()

    def start_scan(self):
        with self._lock:
            self._active_scans += 1

    def finish_scan(self):
        with self._lock:
            self._active_scans = max(0, self._active_scans - 1)

    def add_result(self, msg_id, data):
        with self._lock:
            self._results[msg_id] = {**data, 'timestamp': time.time()}

    def cleanup_results(self):
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._results.items() if now - v.get('timestamp', 0) > self._ttl]
            for k in expired:
                del self._results[k]

    def get_active_count(self):
        with self._lock:
            return self._active_scans

    def get_results_count(self):
        with self._lock:
            return len(self._results)

    def set_ttl(self, ttl):
        with self._lock:
            self._ttl = ttl

    def get_results(self):
        with self._lock:
            return dict(self._results) 