"""
Система управления настройками бота
"""

import json
import os
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import shutil

class SettingsManager:
    """Менеджер настроек бота (только settings.json)"""
    
    # Константы для значений по умолчанию
    DEFAULT_SETTINGS = {
        'monitoring': {
            'enabled': False,
            'interval': 300,
            'auto_start': False,
            'notify_on_change': True
        },
        'notifications': {
            'enabled': True,
            'quiet_hours': {
                'enabled': False,
                'start': '23:00',
                'end': '07:00'
            }
        },
        'scanning': {
            'default_ports': [80, 443, 22, 21, 23, 53, 8080],
            'default_timeout': 5,
            'max_concurrent_scans': 3,
            'results_ttl': 3600
        },
        'routers': {
            'ips': [],
            'ports': [80, 443, 22]
        },
        'security': {
            'operators': []
        }
    }
    
    def __init__(self, config_file: Optional[str] = None, base_dir: Optional[str] = None):
        # Определяем базовую директорию относительно расположения этого файла
        if base_dir is None:
            # Поднимаемся на 2 уровня вверх от utils, затем в telegram_bot/data
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.abspath(os.path.join(current_dir, '../telegram_bot/data'))
        
        self.base_dir = base_dir
        
        if not config_file:
            config_file = os.path.join(self.base_dir, 'settings.json')
        self.config_file = config_file
        
        self._ensure_data_dir()
        self.settings = self._load_settings()
        self._migrate_old_settings()
        logging.info(f"[SETTINGS] Используется файл настроек: {self.config_file}")

    def _ensure_data_dir(self):
        """Создаёт директорию для данных если её нет"""
        dir_name = os.path.dirname(self.config_file)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        
    def _load_settings(self) -> Dict[str, Any]:
        """Загружает настройки из файла или инициализирует значениями по умолчанию"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                logging.info("[SETTINGS] Настройки загружены из файла")
                return self._merge_with_defaults(loaded_settings)
            except Exception as e:
                logging.error(f"[SETTINGS] Ошибка загрузки settings.json: {e}")
                logging.warning("[SETTINGS] Используются настройки по умолчанию")
                return self.DEFAULT_SETTINGS.copy()
        else:
            logging.warning("[SETTINGS] settings.json не найден, инициализация настройками по умолчанию")
            self._save_settings(self.DEFAULT_SETTINGS.copy())
            return self.DEFAULT_SETTINGS.copy()
    
    def _merge_with_defaults(self, loaded_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Объединяет загруженные настройки с настройками по умолчанию"""
        result = self.DEFAULT_SETTINGS.copy()
        
        def merge_dicts(default, custom):
            for key, value in custom.items():
                if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                    merge_dicts(default[key], value)
                else:
                    default[key] = value
        
        merge_dicts(result, loaded_settings)
        return result
    
    def _migrate_old_settings(self):
        """Миграция старых форматов настроек при необходимости"""
        # Пример миграции: если устаревшее поле существует, преобразуем его в новый формат
        if 'monitoring_interval' in self.settings and 'monitoring' not in self.settings:
            self.settings['monitoring'] = {
                'interval': self.settings.pop('monitoring_interval'),
                'enabled': self.settings.pop('monitoring_enabled', False)
            }
            self._save_settings(self.settings)
            logging.info("[SETTINGS] Выполнена миграция старых настроек")
        
    def _save_settings(self, settings: Dict[str, Any]):
        """Сохраняет настройки в файл"""
        try:
            # Создаем резервную копию перед сохранением
            if os.path.exists(self.config_file):
                backup_file = f"{self.config_file}.backup"
                shutil.copy2(self.config_file, backup_file)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            logging.info("[SETTINGS] Настройки сохранены")
        except Exception as e:
            logging.error(f"[SETTINGS] Ошибка сохранения настроек: {e}")
            raise
            
    def get_setting(self, path: str, default: Any = None) -> Any:
        """Получает значение настройки по пути (например, 'monitoring.interval')"""
        keys = path.split('.')
        value = self.settings
        
        try:
            for key in keys:
                if key not in value:
                    return default
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
            
    def set_setting(self, path: str, value: Any, validate: bool = True) -> bool:
        """Устанавливает значение настройки по пути с опциональной валидацией"""
        if validate and not self._validate_setting(path, value):
            logging.warning(f"[SETTINGS] Некорректное значение для {path}: {value}")
            return False
            
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
    
    def _validate_setting(self, path: str, value: Any) -> bool:
        """Валидация значений настроек"""
        if path == 'monitoring.interval':
            return isinstance(value, int) and 10 <= value <= 3600
        elif path == 'scanning.default_timeout':
            return isinstance(value, int) and 1 <= value <= 60
        elif path == 'scanning.max_concurrent_scans':
            return isinstance(value, int) and 1 <= value <= 10
        elif path == 'scanning.results_ttl':
            return isinstance(value, int) and 60 <= value <= 86400
        elif path.endswith('.enabled'):
            return isinstance(value, bool)
        elif path.endswith('.ips') or path.endswith('.ports'):
            return isinstance(value, list) and all(isinstance(item, (int, str)) for item in value)
        
        return True  # Для неизвестных путей пропускаем валидацию
        
    def get_monitoring_settings(self) -> Dict[str, Any]:
        """Получает настройки мониторинга"""
        return self.settings.get('monitoring', {}).copy()
        
    def get_notification_settings(self) -> Dict[str, Any]:
        """Получает настройки уведомлений"""
        return self.settings.get('notifications', {}).copy()
        
    def get_scanning_settings(self) -> Dict[str, Any]:
        """Получает настройки сканирования"""
        return self.settings.get('scanning', {}).copy()
        
    def get_router_settings(self) -> Dict[str, Any]:
        """Получает настройки роутеров"""
        return self.settings.get('routers', {}).copy()
        
    def update_router_ips(self, ips: List[Union[str, int]]) -> bool:
        """Обновляет список IP роутеров"""
        return self.set_setting('routers.ips', [str(ip) for ip in ips])
        
    def update_router_ports(self, ports: List[Union[str, int]]) -> bool:
        """Обновляет список портов роутеров"""
        return self.set_setting('routers.ports', [int(port) for port in ports])
        
    def update_monitoring_interval(self, interval: int) -> bool:
        """Обновляет интервал мониторинга"""
        return self.set_setting('monitoring.interval', interval)
        
    def update_scan_ports(self, ports: List[Union[str, int]]) -> bool:
        """Обновляет порты для сканирования"""
        return self.set_setting('scanning.default_ports', [int(port) for port in ports])
        
    def toggle_monitoring(self, enabled: bool) -> bool:
        """Включает/выключает мониторинг"""
        return self.set_setting('monitoring.enabled', enabled)
        
    def toggle_notifications(self, enabled: bool) -> bool:
        """Включает/выключает уведомления"""
        return self.set_setting('notifications.enabled', enabled)
        
    def get_settings_summary(self, background_monitor=None, notification_manager=None, 
                           scan_manager=None, online_routers: Optional[int] = None, 
                           offline_routers: Optional[int] = None) -> str:
        """Возвращает сводку настроек."""
        monitoring = self.get_monitoring_settings()
        notifications = self.get_notification_settings()
        scanning = self.get_scanning_settings()
        routers = self.get_router_settings()

        summary = "*⚙️ Текущие настройки:*\n\n"

        # Мониторинг
        monitor_enabled = background_monitor.is_running if background_monitor is not None else monitoring.get('enabled', False)
        summary += "*🌐 Мониторинг:*\n"
        summary += f"• Включён: {'✅' if monitor_enabled else '❌'}\n"
        summary += f"• Интервал: `{monitoring.get('interval', 300)}` сек\n"
        summary += f"• Автозапуск: {'✅' if monitoring.get('auto_start', False) else '❌'}\n"
        summary += f"• Уведомления: {'✅' if monitoring.get('notify_on_change', True) else '❌'}\n\n"

        # Уведомления
        notif_enabled = notification_manager.is_running if notification_manager is not None else notifications.get('enabled', True)
        quiet_hours = notifications.get('quiet_hours', {})
        summary += "*🔔 Уведомления:*\n"
        summary += f"• Включены: {'✅' if notif_enabled else '❌'}\n"
        if quiet_hours.get('enabled', False):
            summary += f"• Тихие часы: ✅ ({quiet_hours.get('start', '23:00')}-{quiet_hours.get('end', '07:00')})\n"
        else:
            summary += f"• Тихие часы: ❌\n"
        summary += "\n"

        # Сканирование
        active_scans = scan_manager.get_active_count() if scan_manager else 0
        results_count = scan_manager.get_results_count() if scan_manager else 0
        summary += "*🔍 Сканирование:*\n"
        summary += f"• Активных сканирований: `{active_scans}`\n"
        summary += f"• Активных результатов: `{results_count}`\n"
        summary += f"• Таймаут: `{scanning.get('default_timeout', 5)}` сек\n"
        summary += f"• Макс. сканирований: `{scanning.get('max_concurrent_scans', 3)}`\n"
        summary += f"• TTL результатов: `{scanning.get('results_ttl', 3600)}` сек\n\n"

        # Роутеры
        router_ips = routers.get('ips', [])
        router_ports = routers.get('ports', [])
        summary += "*🌐 Роутеры:*\n"
        summary += f"• Количество (настроено): `{len(router_ips)}`\n"
        
        if online_routers is not None and offline_routers is not None:
            total_known = online_routers + offline_routers
            summary += f"• Количество (факт): `{total_known}`\n"
            summary += f"• Онлайн: `{online_routers}` | Оффлайн: `{offline_routers}`\n"
        
        summary += f"• Порты: `{', '.join(map(str, router_ports))}`\n"

        return summary
        
    def reset_to_defaults(self) -> bool:
        """Сбрасывает настройки к значениям по умолчанию"""
        try:
            self.settings = self.DEFAULT_SETTINGS.copy()
            self._save_settings(self.settings)
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
            # Валидируем импортируемые настройки
            validated_settings = self._merge_with_defaults(new_settings)
            self.settings = validated_settings
            self._save_settings(self.settings)
            logging.info("[SETTINGS] Настройки импортированы и валидированы")
            return True
        except Exception as e:
            logging.error(f"[SETTINGS] Ошибка импорта настроек: {e}")
            return False
            
    def create_backup(self, stats_file: Optional[str] = None) -> str:
        """Создаёт резервную копию настроек и статистики"""
        backup_dir = os.path.join(self.base_dir, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{timestamp}"
        backup_path = os.path.join(backup_dir, backup_name)
        
        files_to_backup = [self.config_file]
        if stats_file and os.path.exists(stats_file):
            files_to_backup.append(stats_file)
            
        try:
            import zipfile
            with zipfile.ZipFile(backup_path + '.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files_to_backup:
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.basename(file_path))
            return backup_path + '.zip'
        except Exception as e:
            return f"ERROR: {str(e)}"

    def get_secret(self, key: str) -> Optional[Any]:
        """Получает секретное значение из secrets.json"""
        try:
            secrets_path = os.path.join(self.base_dir, 'secrets.json')
            if os.path.exists(secrets_path):
                with open(secrets_path, 'r', encoding='utf-8') as f:
                    secrets = json.load(f)
                return secrets.get(key)
            return None
        except Exception as e:
            logging.error(f"[SETTINGS] Ошибка чтения секретов: {e}")
            return None

    def get_admins(self) -> List[int]:
        """Возвращает список ID администраторов"""
        try:
            admins = self.get_secret('admins') or []
            # Преобразуем все значения в int для consistency
            return [int(admin_id) for admin_id in admins if str(admin_id).isdigit()]
        except Exception as e:
            logging.error(f"[SETTINGS] Ошибка получения списка администраторов: {e}")
            return []

    def get_user_role(self, user_id: Union[int, str]) -> str:
        """Возвращает роль пользователя: 'admin', 'operator', 'none'"""
        try:
            user_id_int = int(user_id)
            admins = self.get_admins()
            if user_id_int in admins:
                return 'admin'
                
            operators = self.get_setting('security.operators', [])
            operators_ids = [int(op_id) for op_id in operators if str(op_id).isdigit()]
            if user_id_int in operators_ids:
                return 'operator'
                
            return 'none'
        except (ValueError, TypeError):
            return 'none'
    
    def add_operator(self, user_id: Union[int, str]) -> bool:
        """Добавляет оператора"""
        try:
            user_id_int = int(user_id)
            operators = self.get_setting('security.operators', [])
            if user_id_int not in operators:
                operators.append(user_id_int)
                return self.set_setting('security.operators', operators)
            return True
        except (ValueError, TypeError):
            return False
    
    def remove_operator(self, user_id: Union[int, str]) -> bool:
        """Удаляет оператора"""
        try:
            user_id_int = int(user_id)
            operators = self.get_setting('security.operators', [])
            if user_id_int in operators:
                operators.remove(user_id_int)
                return self.set_setting('security.operators', operators)
            return True
        except (ValueError, TypeError):
            return False
