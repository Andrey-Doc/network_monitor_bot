from .translations import translate
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'settings_menu_btn')), KeyboardButton(translate(lang, 'monitoring_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'scan_menu_btn')), KeyboardButton(translate(lang, 'notification_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'router_menu_btn')), KeyboardButton(translate(lang, 'interface_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'security_menu_btn')), KeyboardButton(translate(lang, 'backup_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'export_menu_btn')), KeyboardButton(translate(lang, 'help_menu_btn')))
    return kb

def settings_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'monitoring_menu_btn')), KeyboardButton(translate(lang, 'scan_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'notification_menu_btn')), KeyboardButton(translate(lang, 'router_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'interface_menu_btn')), KeyboardButton(translate(lang, 'security_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'backup_menu_btn')), KeyboardButton(translate(lang, 'export_menu_btn')))
    kb.row(KeyboardButton(translate(lang, 'help_menu_btn')), KeyboardButton(translate(lang, 'back_to_main_btn')))
    return kb

def monitoring_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'monitoring_interval')), KeyboardButton(translate(lang, 'monitoring_autostart')))
    kb.row(KeyboardButton(translate(lang, 'monitoring_notify_change')), KeyboardButton(translate(lang, 'monitoring_notify_start')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings_btn')))
    return kb

def scan_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'scan_timeout')), KeyboardButton(translate(lang, 'scan_max_concurrent')))
    kb.row(KeyboardButton(translate(lang, 'scan_ports')), KeyboardButton(translate(lang, 'scan_miner_ports')))
    kb.row(KeyboardButton(translate(lang, 'scan_router_ports')), KeyboardButton(translate(lang, 'scan_ttl')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings_btn')))
    return kb

def notification_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'notifications_toggle')), KeyboardButton(translate(lang, 'quiet_hours')))
    kb.row(KeyboardButton(translate(lang, 'notifications_level')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings_btn')))
    return kb

def router_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'router_ips')), KeyboardButton(translate(lang, 'router_ports')))
    kb.row(KeyboardButton(translate(lang, 'router_interval')), KeyboardButton(translate(lang, 'router_status')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings_btn')))
    return kb

def interface_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'interface_language')), KeyboardButton(translate(lang, 'interface_progress')))
    kb.row(KeyboardButton(translate(lang, 'interface_time')), KeyboardButton(translate(lang, 'interface_compact')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings_btn')))
    return kb

def security_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'security_users')), KeyboardButton(translate(lang, 'security_admin_only')))
    kb.row(KeyboardButton(translate(lang, 'security_log_level')), KeyboardButton(translate(lang, 'security_token')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings_btn')))
    return kb

def backup_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'backup_auto')), KeyboardButton(translate(lang, 'backup_interval')))
    kb.row(KeyboardButton(translate(lang, 'backup_max_count')), KeyboardButton(translate(lang, 'backup_now')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings_btn')))
    return kb

def export_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'export_settings')), KeyboardButton(translate(lang, 'import_settings')))
    kb.row(KeyboardButton(translate(lang, 'export_stats')), KeyboardButton(translate(lang, 'export_logs')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings_btn')))
    return kb

def help_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'back_to_settings_btn')), KeyboardButton(translate(lang, 'back_to_main_btn')))
    return kb

def cancel_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'cancel')))
    return kb 