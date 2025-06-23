"""
Система управления настройками бота
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import shutil

class SettingsManager:
    """Менеджер настроек бота"""
    
    def __init__(self, config_file: str = "data/settings.json"):
        self.config_file = config_file
        self.settings = self._load_settings()
        self._ensure_data_dir()
        
    def _ensure_data_dir(self):
        """Создаёт директорию для данных если её нет"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
    def _load_settings(self) -> Dict[str, Any]:
        """Загружает настройки из файла"""
        default_settings = {
            'monitoring': {
                'enabled': True,
                'interval': 300,  # 5 минут
                'auto_start': False,
                'notify_on_change': True,
                'notify_on_startup': True
            },
            'notifications': {
                'enabled': True,
                'levels': ['info', 'warning', 'critical', 'success'],
                'quiet_hours': {
                    'enabled': False,
                    'start': '22:00',
                    'end': '08:00'
                }
            },
            'scanning': {
                'default_timeout': 5,
                'max_concurrent_scans': 3,
                'default_ports': [22, 80, 443, 8080, 8022, 4028],
                'miner_ports': [4028],
                'router_ports': [8080, 8022],
                'results_ttl': 3600
            },
            'routers': {
                'ips': ['11.250.0.1', '11.250.0.2', '11.250.0.3', '11.250.0.4', '11.250.0.5'],
                'ports': [8080, 8022],
                'check_interval': 60
            },
            'interface': {
                'language': 'ru',
                'show_progress': True,
                'show_timestamps': True,
                'compact_mode': False
            },
            'security': {
                'allowed_users': [],
                'admin_only_settings': True,
                'log_level': 'INFO'
            },
            'backup': {
                'auto_backup': True,
                'backup_interval': 86400,  # 24 часа
                'max_backups': 7
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Объединяем с настройками по умолчанию
                    return self._merge_settings(default_settings, loaded_settings)
            else:
                # Создаём файл с настройками по умолчанию
                self._save_settings(default_settings)
                return default_settings
        except Exception as e:
            logging.error(f"[SETTINGS] Ошибка загрузки настроек: {e}")
            return default_settings
            
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
        """Сохраняет настройки в файл"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            logging.info("[SETTINGS] Настройки сохранены")
        except Exception as e:
            logging.error(f"[SETTINGS] Ошибка сохранения настроек: {e}")
            
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
        
    def get_settings_summary(self) -> str:
        """Возвращает сводку настроек"""
        monitoring = self.get_monitoring_settings()
        notifications = self.get_notification_settings()
        scanning = self.get_scanning_settings()
        routers = self.get_router_settings()
        
        summary = "*⚙️ Текущие настройки:*\n\n"
        
        # Мониторинг
        summary += "*🌐 Мониторинг:*\n"
        summary += f"• Включён: {'✅' if monitoring.get('enabled') else '❌'}\n"
        summary += f"• Интервал: `{monitoring.get('interval', 300)}` сек\n"
        summary += f"• Автозапуск: {'✅' if monitoring.get('auto_start') else '❌'}\n"
        summary += f"• Уведомления: {'✅' if monitoring.get('notify_on_change') else '❌'}\n\n"
        
        # Уведомления
        summary += "*🔔 Уведомления:*\n"
        summary += f"• Включены: {'✅' if notifications.get('enabled') else '❌'}\n"
        summary += f"• Тихие часы: {'✅' if notifications.get('quiet_hours', {}).get('enabled') else '❌'}\n\n"
        
        # Сканирование
        summary += "*🔍 Сканирование:*\n"
        summary += f"• Таймаут: `{scanning.get('default_timeout', 5)}` сек\n"
        summary += f"• Макс. сканирований: `{scanning.get('max_concurrent_scans', 3)}`\n"
        summary += f"• TTL результатов: `{scanning.get('results_ttl', 3600)}` сек\n\n"
        
        # Роутеры
        summary += "*🌐 Роутеры:*\n"
        summary += f"• Количество: `{len(routers.get('ips', []))}`\n"
        summary += f"• Порты: `{', '.join(map(str, routers.get('ports', [])))}`\n"
        
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