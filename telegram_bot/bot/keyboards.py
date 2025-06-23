from .translations import translate
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'settings_menu')))
    kb.add(KeyboardButton(translate(lang, 'monitoring_menu')))
    kb.add(KeyboardButton(translate(lang, 'scan_menu')))
    kb.add(KeyboardButton(translate(lang, 'notification_menu')))
    kb.add(KeyboardButton(translate(lang, 'router_menu')))
    kb.add(KeyboardButton(translate(lang, 'interface_menu')))
    kb.add(KeyboardButton(translate(lang, 'security_menu')))
    kb.add(KeyboardButton(translate(lang, 'backup_menu')))
    kb.add(KeyboardButton(translate(lang, 'export_menu')))
    kb.add(KeyboardButton(translate(lang, 'help_menu')))
    return kb

def settings_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'monitoring_menu')))
    kb.add(KeyboardButton(translate(lang, 'scan_menu')))
    kb.add(KeyboardButton(translate(lang, 'notification_menu')))
    kb.add(KeyboardButton(translate(lang, 'router_menu')))
    kb.add(KeyboardButton(translate(lang, 'interface_menu')))
    kb.add(KeyboardButton(translate(lang, 'security_menu')))
    kb.add(KeyboardButton(translate(lang, 'backup_menu')))
    kb.add(KeyboardButton(translate(lang, 'export_menu')))
    kb.add(KeyboardButton(translate(lang, 'help_menu')))
    kb.add(KeyboardButton(translate(lang, 'back_to_main')))
    return kb

def monitoring_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'monitoring_interval')))
    kb.add(KeyboardButton(translate(lang, 'monitoring_autostart')))
    kb.add(KeyboardButton(translate(lang, 'monitoring_notify_change')))
    kb.add(KeyboardButton(translate(lang, 'monitoring_notify_start')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings')))
    return kb

def scan_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'scan_timeout')))
    kb.add(KeyboardButton(translate(lang, 'scan_max_concurrent')))
    kb.add(KeyboardButton(translate(lang, 'scan_ports')))
    kb.add(KeyboardButton(translate(lang, 'scan_miner_ports')))
    kb.add(KeyboardButton(translate(lang, 'scan_router_ports')))
    kb.add(KeyboardButton(translate(lang, 'scan_ttl')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings')))
    return kb

def notification_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'notifications_toggle')))
    kb.add(KeyboardButton(translate(lang, 'quiet_hours')))
    kb.add(KeyboardButton(translate(lang, 'notifications_level')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings')))
    return kb

def router_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'router_ips')))
    kb.add(KeyboardButton(translate(lang, 'router_ports')))
    kb.add(KeyboardButton(translate(lang, 'router_interval')))
    kb.add(KeyboardButton(translate(lang, 'router_status')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings')))
    return kb

def interface_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'interface_language')))
    kb.add(KeyboardButton(translate(lang, 'interface_progress')))
    kb.add(KeyboardButton(translate(lang, 'interface_time')))
    kb.add(KeyboardButton(translate(lang, 'interface_compact')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings')))
    return kb

def security_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'security_users')))
    kb.add(KeyboardButton(translate(lang, 'security_admin_only')))
    kb.add(KeyboardButton(translate(lang, 'security_log_level')))
    kb.add(KeyboardButton(translate(lang, 'security_token')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings')))
    return kb

def backup_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'backup_auto')))
    kb.add(KeyboardButton(translate(lang, 'backup_interval')))
    kb.add(KeyboardButton(translate(lang, 'backup_max_count')))
    kb.add(KeyboardButton(translate(lang, 'backup_now')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings')))
    return kb

def export_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'export_settings')))
    kb.add(KeyboardButton(translate(lang, 'import_settings')))
    kb.add(KeyboardButton(translate(lang, 'export_stats')))
    kb.add(KeyboardButton(translate(lang, 'export_logs')))
    kb.add(KeyboardButton(translate(lang, 'back_to_settings')))
    return kb

def help_menu_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'back_to_settings')))
    kb.add(KeyboardButton(translate(lang, 'back_to_main')))
    return kb

def cancel_keyboard(lang=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(translate(lang, 'cancel')))
    return kb 