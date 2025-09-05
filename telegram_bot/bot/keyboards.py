from .translations import translate
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard(lang=None, role=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'status_main_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'router_status_main_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'snmp_router_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'scan_main_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'asic_status_main_menu_btn')))
    # Кнопка "Настройки" для операторов и админов
    if role in ('admin', 'operator'):
        kb.row(KeyboardButton(translate(lang, 'settings_main_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'help_btn')))
    return kb

def settings_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'monitoring_menu_btn')), KeyboardButton(translate(lang, 'scan_settings_btn')))
    kb.row(KeyboardButton(translate(lang, 'notification_menu_btn')), KeyboardButton(translate(lang, 'router_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'interface_menu_btn')), KeyboardButton(translate(lang, 'security_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'backup_menu_btn')), KeyboardButton(translate(lang, 'export_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'help_menu_btn')), KeyboardButton(translate(lang, 'back_to_main_btn')))
    return kb

def monitoring_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'monitoring_interval_btn')), KeyboardButton(translate(lang, 'monitoring_autostart_btn')))
    kb.row(KeyboardButton(translate(lang, 'monitoring_notify_change_btn')), KeyboardButton(translate(lang, 'monitoring_notify_start_btn')))
    kb.add(KeyboardButton(translate(lang, 'settings_main_menu_btn')))
    return kb

def scan_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'scan_timeout_btn')), KeyboardButton(translate(lang, 'scan_max_concurrent_btn')))
    kb.row(KeyboardButton(translate(lang, 'scan_ports_btn')), KeyboardButton(translate(lang, 'scan_miner_ports_btn')))
    kb.row(KeyboardButton(translate(lang, 'scan_router_ports_btn')), KeyboardButton(translate(lang, 'scan_ttl_btn')))
    kb.add(KeyboardButton(translate(lang, 'settings_main_menu_btn')))
    return kb

def notification_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'notifications_toggle_btn')), KeyboardButton(translate(lang, 'quiet_hours_btn')))
    kb.row(KeyboardButton(translate(lang, 'notifications_level_btn')))
    kb.add(KeyboardButton(translate(lang, 'settings_main_menu_btn')))
    return kb

def router_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'router_ips_btn')), KeyboardButton(translate(lang, 'router_ports_btn')))
    kb.row(KeyboardButton(translate(lang, 'router_interval_btn')), KeyboardButton(translate(lang, 'router_status_btn')))
    kb.add(KeyboardButton(translate(lang, 'settings_main_menu_btn')))
    return kb

def interface_menu_keyboard(lang=None, role=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    # Кнопка "Язык интерфейса" доступна всем, остальные — только админам
    kb.row(KeyboardButton(translate(lang, 'interface_language_btn')))
    if role == 'admin':
        kb.row(KeyboardButton(translate(lang, 'interface_progress_btn')),
               KeyboardButton(translate(lang, 'interface_time_btn')))
        kb.row(KeyboardButton(translate(lang, 'interface_compact_btn')))
    kb.add(KeyboardButton(translate(lang, 'settings_main_menu_btn')))
    return kb

def security_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'security_users_btn')))
    kb.row(KeyboardButton(translate(lang, 'security_log_level_btn')))
    kb.row(KeyboardButton(translate(lang, 'security_access_control_btn')))
    kb.row(KeyboardButton(translate(lang, 'back_to_settings_btn')))
    return kb

def backup_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'backup_auto_btn')), KeyboardButton(translate(lang, 'backup_interval_btn')))
    kb.row(KeyboardButton(translate(lang, 'backup_max_count_btn')), KeyboardButton(translate(lang, 'backup_now_btn')))
    kb.add(KeyboardButton(translate(lang, 'settings_main_menu_btn')))
    return kb

def export_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'export_settings_btn')), KeyboardButton(translate(lang, 'import_settings_btn')))
    kb.row(KeyboardButton(translate(lang, 'export_stats_btn')), KeyboardButton(translate(lang, 'export_logs_btn')))
    kb.add(KeyboardButton(translate(lang, 'settings_main_menu_btn')))
    return kb

def help_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'help_bot_btn')))
    kb.row(KeyboardButton(translate(lang, 'back_to_main_btn')))
    return kb

def cancel_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'cancel')))
    return kb

# Главное меню сканирования
def scan_main_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'scan_network_main_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'scan_miners_main_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'fast_scan_main_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'scan_files_main_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'upload_file_main_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'back_to_main_btn')))
    return kb

# Главное меню настроек
def settings_main_menu_keyboard(lang=None, role=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    if role == 'admin':
        kb.row(KeyboardButton(translate(lang, 'monitoring_menu_btn')), KeyboardButton(translate(lang, 'scan_menu_btn')))
        kb.row(KeyboardButton(translate(lang, 'notification_menu_btn')), KeyboardButton(translate(lang, 'router_menu_btn')))
        kb.row(KeyboardButton(translate(lang, 'interface_menu_btn')))
        kb.row(KeyboardButton(translate(lang, 'security_menu_btn')), KeyboardButton(translate(lang, 'backup_menu_btn')))
        kb.row(KeyboardButton(translate(lang, 'export_menu_btn')), KeyboardButton(translate(lang, 'help_menu_btn')))
        kb.row(KeyboardButton(translate(lang, 'asic_ips_btn')))
    elif role == 'operator':
        kb.row(KeyboardButton(translate(lang, 'monitoring_menu_btn')), KeyboardButton(translate(lang, 'scan_menu_btn')))
        kb.row(KeyboardButton(translate(lang, 'notification_menu_btn')), KeyboardButton(translate(lang, 'router_menu_btn')))
        kb.row(KeyboardButton(translate(lang, 'interface_menu_btn')))
        kb.row(KeyboardButton(translate(lang, 'backup_menu_btn')), KeyboardButton(translate(lang, 'export_menu_btn')))
        kb.row(KeyboardButton(translate(lang, 'help_menu_btn')))
        kb.row(KeyboardButton(translate(lang, 'asic_ips_btn')))
    else:
        kb.row(KeyboardButton(translate(lang, 'help_menu_btn')))
    kb.add(KeyboardButton(translate(lang, 'back_to_main_btn')))
    return kb

def scan_cancel_or_main_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'cancel_btn')), KeyboardButton(translate(lang, 'back_to_main_btn')))
    return kb

def asic_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'asic_ips_btn')))
    kb.add(KeyboardButton(translate(lang, 'settings_main_menu_btn')))
    return kb

def asic_ips_cancel_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'cancel_btn')))
    return kb 