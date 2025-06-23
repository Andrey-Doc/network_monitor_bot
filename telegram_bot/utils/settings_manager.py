"""
Система управления настройками бота
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import shutil
import importlib.util

class SettingsManager:
    """Менеджер настроек бота с синхронизацией config.py <-> settings.json"""
    
    def __init__(self, config_file: str = "data/settings.json", config_py: str = "bot/config.py"):
        self.config_file = config_file
        self.config_py = config_py
        self.config_py_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", config_py))
        self.config_dict = self._load_config_py()
        self.settings = self._load_settings()
        self._ensure_data_dir()
        
    def _ensure_data_dir(self):
        """Создаёт директорию для данных если её нет"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
    def _load_config_py(self) -> dict:
        """Загружает CONFIG из config.py как словарь"""
        try:
            spec = importlib.util.spec_from_file_location("config", self.config_py_path)
            config_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_mod)
            config = dict(getattr(config_mod, "CONFIG", {}))
            if not config:
                logging.warning("[SETTINGS] CONFIG из config.py пустой! Проверьте структуру config.py.")
            else:
                logging.info(f"[SETTINGS] CONFIG из config.py: {config}")
            return config
        except Exception as e:
            logging.error(f"[SETTINGS] Ошибка загрузки config.py: {e}")
            return {}
        
    def _load_settings(self) -> Dict[str, Any]:
        """Загружает настройки из файла или инициализирует из config.py"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                # Объединяем с config.py (config.py — источник по умолчанию)
                merged = self._merge_settings(self.config_dict, loaded_settings)
                if not merged:
                    logging.warning("[SETTINGS] settings.json пустой, инициализация из config.py")
                    self._save_settings(self.config_dict)
                    return self.config_dict.copy()
                return merged
            except Exception as e:
                logging.error(f"[SETTINGS] Ошибка загрузки settings.json: {e}")
                return self.config_dict.copy()
        else:
            # Если файла нет — инициализируем из config.py
            if not self.config_dict:
                logging.warning("[SETTINGS] config.py пустой, settings.json не будет создан!")
                return {}
            self._save_settings(self.config_dict)
            return self.config_dict.copy()
        
    def _merge_settings(self, default: Dict, loaded: Dict) -> Dict:
        """Объединяет настройки по умолчанию с загруженными"""
        result = default.copy()
        
        def merge_dicts(base, update):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dicts(base[key], value)
                else:
                    base[key] = value
                    
        merge_dicts(result, loaded)
        return result
        
    def _save_settings(self, settings: Dict[str, Any]):
        """Сохраняет настройки в файл и обновляет config.py"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            self._update_config_py(settings)
            logging.info("[SETTINGS] Настройки сохранены и config.py обновлён")
        except Exception as e:
            logging.error(f"[SETTINGS] Ошибка сохранения настроек: {e}")
            
    def _update_config_py(self, settings: Dict[str, Any]):
        """Обновляет CONFIG в config.py на основе settings"""
        try:
            lines = ["CONFIG = {\n"]
            for k, v in settings.items():
                lines.append(f"    {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)},\n")
            lines.append("}\n")
            with open(self.config_py_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        except Exception as e:
            logging.error(f"[SETTINGS] Ошибка обновления config.py: {e}")
            
    def get_setting(self, path: str, default: Any = None) -> Any:
        """Получает значение настройки по пути (например, 'monitoring.interval')"""
        keys = path.split('.')
        value = self.settings
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
            
    def set_setting(self, path: str, value: Any) -> bool:
        """Устанавливает значение настройки по пути"""
        keys = path.split('.')
        current = self.settings
        
        try:
            # Проходим по пути до последнего элемента
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            # Устанавливаем значение
            current[keys[-1]] = value
            
            # Сохраняем настройки
            self._save_settings(self.settings)
            logging.info(f"[SETTINGS] Настройка {path} изменена на {value}")
            return True
        except Exception as e:
            logging.error(f"[SETTINGS] Ошибка установки настройки {path}: {e}")
            return False
            
    def get_monitoring_settings(self) -> Dict[str, Any]:
        """Получает настройки мониторинга"""
        return self.settings.get('monitoring', {})
        
    def get_notification_settings(self) -> Dict[str, Any]:
        """Получает настройки уведомлений"""
        return self.settings.get('notifications', {})
        
    def get_scanning_settings(self) -> Dict[str, Any]:
        """Получает настройки сканирования"""
        return self.settings.get('scanning', {})
        
    def get_router_settings(self) -> Dict[str, Any]:
        """Получает настройки роутеров"""
        return self.settings.get('routers', {})
        
    def update_router_ips(self, ips: list) -> bool:
        """Обновляет список IP роутеров"""
        return self.set_setting('routers.ips', ips)
        
    def update_router_ports(self, ports: list) -> bool:
        """Обновляет список портов роутеров"""
        return self.set_setting('routers.ports', ports)
        
    def update_monitoring_interval(self, interval: int) -> bool:
        """Обновляет интервал мониторинга"""
        return self.set_setting('monitoring.interval', interval)
        
    def update_scan_ports(self, ports: list) -> bool:
        """Обновляет порты для сканирования"""
        return self.set_setting('scanning.default_ports', ports)
        
    def toggle_monitoring(self, enabled: bool) -> bool:
        """Включает/выключает мониторинг"""
        return self.set_setting('monitoring.enabled', enabled)
        
    def toggle_notifications(self, enabled: bool) -> bool:
        """Включает/выключает уведомления"""
        return self.set_setting('notifications.enabled', enabled)
        
    def get_settings_summary(self, background_monitor=None, notification_manager=None, scan_manager=None, online_routers=None, offline_routers=None) -> str:
        """Возвращает сводку настроек. Статус мониторинга и уведомлений определяется по фактическому состоянию, если переданы объекты. Количество активных сканирований и результатов — из scan_manager. Количество онлайн/оффлайн роутеров — из параметров."""
        monitoring = self.get_monitoring_settings()
        notifications = self.get_notification_settings()
        scanning = self.get_scanning_settings()
        routers = self.get_router_settings()

        summary = "*⚙️ Текущие настройки:*\n\n"

        # Мониторинг
        monitor_enabled = background_monitor.is_running if background_monitor is not None else monitoring.get('enabled')
        summary += "*🌐 Мониторинг:*\n"
        summary += f"• Включён: {'✅' if monitor_enabled else '❌'}\n"
        summary += f"• Интервал: `{monitoring.get('interval', 300)}` сек\n"
        summary += f"• Автозапуск: {'✅' if monitoring.get('auto_start') else '❌'}\n"
        summary += f"• Уведомления: {'✅' if monitoring.get('notify_on_change') else '❌'}\n\n"

        # Уведомления
        notif_enabled = notification_manager.is_running if notification_manager is not None else notifications.get('enabled')
        summary += "*🔔 Уведомления:*\n"
        summary += f"• Включены: {'✅' if notif_enabled else '❌'}\n"
        summary += f"• Тихие часы: {'✅' if notifications.get('quiet_hours', {}).get('enabled') else '❌'}\n\n"

        # Сканирование
        active_scans = scan_manager.get_active_count() if scan_manager else scanning.get('active_scans', 0)
        results_count = scan_manager.get_results_count() if scan_manager else scanning.get('results_count', 0)
        summary += "*🔍 Сканирование:*\n"
        summary += f"• Активных сканирований: `{active_scans}`\n"
        summary += f"• Активных результатов: `{results_count}`\n"
        summary += f"• Таймаут: `{scanning.get('default_timeout', 5)}` сек\n"
        summary += f"• Макс. сканирований: `{scanning.get('max_concurrent_scans', 3)}`\n"
        summary += f"• TTL результатов: `{scanning.get('results_ttl', 3600)}` сек\n\n"

        # Роутеры
        summary += "*🌐 Роутеры:*\n"
        summary += f"• Количество: `{len(routers.get('ips', []))}`\n"
        summary += f"• Порты: `{', '.join(map(str, routers.get('ports', [])))}`\n"
        if online_routers is not None and offline_routers is not None:
            summary += f"• Онлайн: `{online_routers}` | Оффлайн: `{offline_routers}`\n"

        return summary
        
    def reset_to_defaults(self) -> bool:
        """Сбрасывает настройки к значениям по умолчанию"""
        try:
            # Удаляем файл настроек
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
            
            # Перезагружаем настройки
            self.settings = self._load_settings()
            logging.info("[SETTINGS] Настройки сброшены к значениям по умолчанию")
            return True
        except Exception as e:
            logging.error(f"[SETTINGS] Ошибка сброса настроек: {e}")
            return False
            
    def export_settings(self) -> str:
        """Экспортирует настройки в JSON"""
        try:
            return json.dumps(self.settings, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"[SETTINGS] Ошибка экспорта настроек: {e}")
            return "{}"
            
    def import_settings(self, settings_json: str) -> bool:
        """Импортирует настройки из JSON"""
        try:
            new_settings = json.loads(settings_json)
            self.settings = self._merge_settings(self.settings, new_settings)
            self._save_settings(self.settings)
            logging.info("[SETTINGS] Настройки импортированы")
            return True
        except Exception as e:
            logging.error(f"[SETTINGS] Ошибка импорта настроек: {e}")
            return False
            
    def create_backup(self, stats_file: str = None) -> str:
        """Создаёт резервную копию настроек (и статистики, если указано) в папке data/backups. Возвращает путь к архиву или ошибку."""
        backup_dir = os.path.join(os.path.dirname(self.config_file), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_name)
        files_to_backup = [self.config_file]
        if stats_file and os.path.exists(stats_file):
            files_to_backup.append(stats_file)
        try:
            # Создаём zip-архив
            shutil.make_archive(backup_path, 'zip', root_dir=os.path.dirname(self.config_file), base_dir='settings.json')
            # Добавляем статистику, если есть
            if stats_file and os.path.exists(stats_file):
                import zipfile
                with zipfile.ZipFile(backup_path + '.zip', 'a') as zf:
                    zf.write(stats_file, arcname=os.path.basename(stats_file))
            return backup_path + '.zip'
        except Exception as e:
            return f"ERROR: {e}" 