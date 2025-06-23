from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery

def get_main_inline_keyboard():
    """Главное меню с inline-кнопками"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🌐 Статус роутеров", callback_data="status_routers"),
        InlineKeyboardButton("🔍 Сканировать сеть", callback_data="scan_network"),
    )
    keyboard.add(
        InlineKeyboardButton("⛏️ Сканировать майнеры", callback_data="scan_miners"),
        InlineKeyboardButton("⚡ Быстрое сканирование", callback_data="fast_scan"),
    )
    keyboard.add(
        InlineKeyboardButton("📊 Статистика", callback_data="statistics"),
        InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
    )
    keyboard.add(
        InlineKeyboardButton("📋 Помощь", callback_data="help"),
    )
    return keyboard

def get_monitoring_control_keyboard():
    """Кнопки управления мониторингом"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("▶️ Запустить мониторинг", callback_data="monitor_start"),
        InlineKeyboardButton("⏸️ Остановить мониторинг", callback_data="monitor_stop"),
    )
    keyboard.add(
        InlineKeyboardButton("🔄 Статус мониторинга", callback_data="monitor_status"),
        InlineKeyboardButton("⚙️ Настройки мониторинга", callback_data="monitor_settings"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"),
    )
    return keyboard

def get_scan_options_keyboard():
    """Кнопки опций сканирования"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔍 Полное сканирование", callback_data="scan_full"),
        InlineKeyboardButton("⚡ Быстрое сканирование", callback_data="scan_fast"),
    )
    keyboard.add(
        InlineKeyboardButton("🎯 Сканировать майнеры", callback_data="scan_miners_only"),
        InlineKeyboardButton("🌐 Сканировать роутеры", callback_data="scan_routers_only"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"),
    )
    return keyboard

def get_network_input_keyboard():
    """Кнопки для ввода сети"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("192.168.1.0/24", callback_data="network_192.168.1.0/24"),
        InlineKeyboardButton("10.0.0.0/24", callback_data="network_10.0.0.0/24"),
    )
    keyboard.add(
        InlineKeyboardButton("172.16.0.0/24", callback_data="network_172.16.0.0/24"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_scan"),
    )
    return keyboard

def get_settings_keyboard():
    """Главное меню настроек"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🌐 Мониторинг", callback_data="settings_monitoring"),
        InlineKeyboardButton("🔔 Уведомления", callback_data="settings_notifications"),
    )
    keyboard.add(
        InlineKeyboardButton("🔍 Сканирование", callback_data="settings_scanning"),
        InlineKeyboardButton("🌐 Роутеры", callback_data="settings_routers"),
    )
    keyboard.add(
        InlineKeyboardButton("🎨 Интерфейс", callback_data="settings_interface"),
        InlineKeyboardButton("🔒 Безопасность", callback_data="settings_security"),
    )
    keyboard.add(
        InlineKeyboardButton("💾 Резервное копирование", callback_data="settings_backup"),
        InlineKeyboardButton("📊 Экспорт/Импорт", callback_data="settings_export"),
    )
    keyboard.add(
        InlineKeyboardButton("🔄 Сбросить настройки", callback_data="settings_reset"),
        InlineKeyboardButton("📋 Сводка", callback_data="settings_summary"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"),
    )
    return keyboard

def get_monitoring_settings_keyboard():
    """Настройки мониторинга"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("⏰ Интервал мониторинга", callback_data="setting_monitor_interval"),
        InlineKeyboardButton("🔄 Автозапуск", callback_data="setting_monitor_auto_start"),
    )
    keyboard.add(
        InlineKeyboardButton("🔔 Уведомления об изменениях", callback_data="setting_monitor_notify_change"),
        InlineKeyboardButton("🚀 Уведомления при запуске", callback_data="setting_monitor_notify_startup"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад к настройкам", callback_data="settings"),
    )
    return keyboard

def get_notification_settings_keyboard():
    """Настройки уведомлений"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔔 Включить/выключить", callback_data="setting_notifications_toggle"),
        InlineKeyboardButton("🔕 Тихие часы", callback_data="setting_notifications_quiet_hours"),
    )
    keyboard.add(
        InlineKeyboardButton("📊 Уровни уведомлений", callback_data="setting_notifications_levels"),
        InlineKeyboardButton("⏰ Время тихих часов", callback_data="setting_notifications_quiet_time"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад к настройкам", callback_data="settings"),
    )
    return keyboard

def get_scanning_settings_keyboard():
    """Настройки сканирования"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("⏱️ Таймаут сканирования", callback_data="setting_scan_timeout"),
        InlineKeyboardButton("🔢 Макс. параллельных сканирований", callback_data="setting_scan_max_concurrent"),
    )
    keyboard.add(
        InlineKeyboardButton("🔌 Порты для сканирования", callback_data="setting_scan_ports"),
        InlineKeyboardButton("⛏️ Порты майнеров", callback_data="setting_scan_miner_ports"),
    )
    keyboard.add(
        InlineKeyboardButton("🌐 Порты роутеров", callback_data="setting_scan_router_ports"),
        InlineKeyboardButton("⏰ TTL результатов", callback_data="setting_scan_ttl"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад к настройкам", callback_data="settings"),
    )
    return keyboard

def get_router_settings_keyboard():
    """Настройки роутеров"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🌐 IP адреса роутеров", callback_data="setting_routers_ips"),
        InlineKeyboardButton("🔌 Порты роутеров", callback_data="setting_routers_ports"),
    )
    keyboard.add(
        InlineKeyboardButton("⏰ Интервал проверки", callback_data="setting_routers_check_interval"),
        InlineKeyboardButton("📊 Статус роутеров", callback_data="setting_routers_status"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад к настройкам", callback_data="settings"),
    )
    return keyboard

def get_interface_settings_keyboard():
    """Настройки интерфейса"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🌍 Язык интерфейса", callback_data="setting_interface_language"),
        InlineKeyboardButton("📊 Показывать прогресс", callback_data="setting_interface_progress"),
    )
    keyboard.add(
        InlineKeyboardButton("🕐 Показывать время", callback_data="setting_interface_timestamps"),
        InlineKeyboardButton("📱 Компактный режим", callback_data="setting_interface_compact"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад к настройкам", callback_data="settings"),
    )
    return keyboard

def get_security_settings_keyboard():
    """Настройки безопасности"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("👥 Разрешенные пользователи", callback_data="setting_security_users"),
        InlineKeyboardButton("🔒 Только админ настройки", callback_data="setting_security_admin_only"),
    )
    keyboard.add(
        InlineKeyboardButton("📝 Уровень логирования", callback_data="setting_security_log_level"),
        InlineKeyboardButton("🔐 Изменить токен", callback_data="setting_security_token"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад к настройкам", callback_data="settings"),
    )
    return keyboard

def get_backup_settings_keyboard():
    """Настройки резервного копирования"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💾 Авторезервное копирование", callback_data="setting_backup_auto"),
        InlineKeyboardButton("⏰ Интервал резервного копирования", callback_data="setting_backup_interval"),
    )
    keyboard.add(
        InlineKeyboardButton("📦 Макс. количество резервных копий", callback_data="setting_backup_max_count"),
        InlineKeyboardButton("💾 Создать резервную копию сейчас", callback_data="setting_backup_create_now"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад к настройкам", callback_data="settings"),
    )
    return keyboard

def get_export_settings_keyboard():
    """Настройки экспорта/импорта"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📄 Экспорт настроек", callback_data="setting_export_settings"),
        InlineKeyboardButton("📥 Импорт настроек", callback_data="setting_import_settings"),
    )
    keyboard.add(
        InlineKeyboardButton("📊 Экспорт статистики", callback_data="setting_export_stats"),
        InlineKeyboardButton("📋 Экспорт логов", callback_data="setting_export_logs"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад к настройкам", callback_data="settings"),
    )
    return keyboard

def get_interval_keyboard():
    """Кнопки для выбора интервала"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("30 сек", callback_data="interval_30"),
        InlineKeyboardButton("1 мин", callback_data="interval_60"),
    )
    keyboard.add(
        InlineKeyboardButton("5 мин", callback_data="interval_300"),
        InlineKeyboardButton("10 мин", callback_data="interval_600"),
    )
    keyboard.add(
        InlineKeyboardButton("30 мин", callback_data="interval_1800"),
        InlineKeyboardButton("1 час", callback_data="interval_3600"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings"),
    )
    return keyboard

def get_toggle_keyboard(current_state: bool):
    """Кнопки включения/выключения"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    if current_state:
        keyboard.add(InlineKeyboardButton("❌ Выключить", callback_data="toggle_off"))
    else:
        keyboard.add(InlineKeyboardButton("✅ Включить", callback_data="toggle_on"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings"))
    return keyboard

def get_export_keyboard():
    """Кнопки экспорта данных"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📄 CSV", callback_data="export_csv"),
        InlineKeyboardButton("📊 Excel", callback_data="export_excel"),
    )
    keyboard.add(
        InlineKeyboardButton("📋 JSON", callback_data="export_json"),
        InlineKeyboardButton("📈 График", callback_data="export_chart"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"),
    )
    return keyboard

def get_help_keyboard():
    """Кнопки помощи"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📖 Команды", callback_data="help_commands"),
        InlineKeyboardButton("🔧 Настройка", callback_data="help_setup"),
    )
    keyboard.add(
        InlineKeyboardButton("❓ FAQ", callback_data="help_faq"),
        InlineKeyboardButton("🐛 Отчёт об ошибке", callback_data="help_bug_report"),
    )
    keyboard.add(
        InlineKeyboardButton("🚀 Возможности", callback_data="help_features"),
        InlineKeyboardButton("🔧 Устранение неполадок", callback_data="help_troubleshooting"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"),
    )
    return keyboard

def get_help_submenu_keyboard():
    """Подменю помощи с дополнительными опциями"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔍 Поиск по справке", callback_data="help_search"),
        InlineKeyboardButton("📋 Все разделы", callback_data="help_all_sections"),
    )
    keyboard.add(
        InlineKeyboardButton("📞 Связаться с поддержкой", callback_data="help_contact"),
        InlineKeyboardButton("📚 Документация", callback_data="help_docs"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад к помощи", callback_data="help"),
    )
    return keyboard

# Удалён устаревший обработчик handle_callback_query, используйте основной обработчик в main.py 