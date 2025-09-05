import os
import time
import threading
import csv
import json
import re

class ScanManager:
    def __init__(self, ttl=3600, results_dir=None):
        self._active_scans = 0
        self._results = {}
        self._ttl = ttl
        self._lock = threading.Lock()
        self._results_dir = results_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/scan_results'))
        os.makedirs(self._results_dir, exist_ok=True)
        self._result_map_path = os.path.join(self._results_dir, 'result_map.json')
        self._result_map = self._load_result_map()

    def _load_result_map(self):
        if os.path.exists(self._result_map_path):
            try:
                with open(self._result_map_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_result_map(self):
        try:
            with open(self._result_map_path, 'w', encoding='utf-8') as f:
                json.dump(self._result_map, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _network_to_filename(self, scan_type, network):
        # network: '10.1.0.0/21' -> '10.1.0.0_21'
        net = network.replace('/', '_').replace('.', '_')
        return f'{scan_type}_{net}'

    def save_scan_result(self, scan_type, network, data, as_csv=True):
        """Сохраняет результат сканирования, удаляя предыдущий для этой сети и типа."""
        self.cleanup_old_scan_results_for_network(scan_type, network)
        base = self._network_to_filename(scan_type, network)
        json_path = os.path.join(self._results_dir, f'{base}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if as_csv:
            items = data.get('devices') or data.get('miners')
            if items:
                csv_path = os.path.join(self._results_dir, f'{base}.csv')
                keys = set()
                for d in items:
                    keys.update(d.keys())
                keys = list(keys)
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    for d in items:
                        writer.writerow(d)

    def get_scan_result_file(self, scan_type, network, ext='csv'):
        base = self._network_to_filename(scan_type, network)
        path = os.path.join(self._results_dir, f'{base}.{ext}')
        return path if os.path.exists(path) else None

    def cleanup_old_scan_results_for_network(self, scan_type, network):
        """Удаляет старые результаты для этой сети и типа сканирования."""
        base = self._network_to_filename(scan_type, network)
        for ext in ('.json', '.csv'):
            path = os.path.join(self._results_dir, f'{base}{ext}')
            if os.path.exists(path):
                os.remove(path)

    def start_scan(self):
        with self._lock:
            self._active_scans += 1

    def finish_scan(self):
        with self._lock:
            self._active_scans = max(0, self._active_scans - 1)

    def add_result(self, msg_id, data):
        with self._lock:
            self._results[msg_id] = {**data, 'timestamp': time.time()}
            # Сохраняем соответствие msg_id → file_path
            file_path = os.path.join(self._results_dir, f'result_{msg_id}.csv')
            self._result_map[str(msg_id)] = file_path
            self._save_result_map()
            # Не сохраняем result_{msg_id}.* файлы больше!

    def _save_devices_csv(self, msg_id, devices):
        csv_path = os.path.join(self._results_dir, f'result_{msg_id}.csv')
        if not devices:
            return
        keys = set()
        for d in devices:
            keys.update(d.keys())
        keys = list(keys)
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for d in devices:
                writer.writerow(d)

    def _save_miners_csv(self, msg_id, miners):
        csv_path = os.path.join(self._results_dir, f'result_{msg_id}.csv')
        if not miners:
            return
        keys = set()
        for m in miners:
            keys.update(m.keys())
        keys = list(keys)
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for m in miners:
                writer.writerow(m)

    def cleanup_results(self):
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._results.items() if now - v.get('timestamp', 0) > self._ttl]
            for k in expired:
                del self._results[k]
                # Удаляем файлы
                for ext in ('.json', '.csv'):
                    path = os.path.join(self._results_dir, f'result_{k}{ext}')
                    if os.path.exists(path):
                        os.remove(path)
                # Удаляем из map
                self._result_map.pop(str(k), None)
            self._save_result_map()

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

    def get_result_file(self, msg_id, ext='csv'):
        # Сначала ищем в map
        file_path = self._result_map.get(str(msg_id))
        if file_path and os.path.exists(file_path):
            return file_path
        # Старый способ
        path = os.path.join(self._results_dir, f'result_{msg_id}.{ext}')
        return path if os.path.exists(path) else None

    def get_result_json(self, msg_id):
        path = os.path.join(self._results_dir, f'result_{msg_id}.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def get_scan_type_for_result(self, result):
        t = result.get('type')
        if t == 'devices':
            return 'scan'
        elif t == 'miners':
            return 'miners'
        elif t == 'fast_scan':
            return 'fast_scan'
        return None 