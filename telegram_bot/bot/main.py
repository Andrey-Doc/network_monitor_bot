import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import Message, ContentType, ReplyKeyboardMarkup, KeyboardButton, InputFile, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from .keyboards import (
    main_menu_keyboard, settings_main_menu_keyboard, monitoring_menu_keyboard,
    scan_menu_keyboard, notification_menu_keyboard, router_menu_keyboard,
    interface_menu_keyboard, security_menu_keyboard, backup_menu_keyboard,
    export_menu_keyboard, help_menu_keyboard, cancel_keyboard,
    scan_main_menu_keyboard, scan_cancel_or_main_keyboard,
    asic_ips_cancel_keyboard
)
from ..utils.router_monitor import check_routers_status
from ..utils.miner_scan import scan_network_for_miners, scan_miners_from_list, get_asic_status
from ..utils.background_monitor import BackgroundMonitor
from ..utils.notifications import NotificationManager, NotificationLevel, NotificationType
from ..utils.statistics import StatisticsManager
from ..utils.settings_manager import SettingsManager
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
import pandas as pd
import os
from ..utils.network_scan import scan_network_devices
import ipaddress
from ..utils.fast_scan import fast_scan_network
import time
import asyncio
from ..utils.help_system import HelpSystem
from .translations import translate
from ..utils.scan_manager import ScanManager
import json
from telegram_bot.utils.snmp_utils import async_get_snmp_full_info, async_get_snmp_info_subprocess
import io
import re
import csv
import glob

logging.basicConfig(level=logging.INFO)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))
settings_manager = SettingsManager(base_dir=BASE_DIR)

def load_secrets():
    secrets_path = os.path.join(BASE_DIR, 'secrets.json')
    with open(secrets_path, 'r', encoding='utf-8') as f:
        return json.load(f)

secrets = load_secrets()
TELEGRAM_BOT_TOKEN = secrets.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = secrets.get('CHAT_ID')
ROUTER_IPS = secrets.get('ROUTER_IPS', [])
ROUTER_PORTS = secrets.get('ROUTER_PORTS', [])
SCAN_RESULTS_TTL = secrets.get('SCAN_RESULTS_TTL', 3600)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Инициализация ScanManager
scan_manager = ScanManager(ttl=settings_manager.get_setting('scanning.results_ttl', 3600))

# Инициализация новых модулей
background_monitor = BackgroundMonitor(bot, CHAT_ID)
notification_manager = NotificationManager(bot, CHAT_ID)
statistics_manager = StatisticsManager(BASE_DIR)
help_system = HelpSystem()

# SCAN_RESULTS_TTL: сначала из настроек, потом из config.py
SCAN_RESULTS_TTL = settings_manager.get_setting('scanning.results_ttl') or SCAN_RESULTS_TTL
# DEFAULT_TIMEOUT: сначала из настроек, потом дефолт
DEFAULT_TIMEOUT = settings_manager.get_setting('scanning.default_timeout') or 5

def get_lang(message=None):
    if message is not None:
        user_id = str(message.from_user.id)
        return settings_manager.get_setting(f'user_languages.{user_id}', 'en')
    return settings_manager.get_setting('interface.language', 'en')

def cleanup_old_results():
    """Очищает старые результаты сканирования"""
    scan_manager.cleanup_results()
    logging.info(f"[CLEANUP] Удалено устаревших результатов сканирования")

class ScanDevicesState(StatesGroup):
    waiting_for_network = State()
    waiting_for_file_request = State()
    waiting_for_timeout = State()

class ScanMinersState(StatesGroup):
    waiting_for_network = State()
    waiting_for_file_request = State()

class FastScanState(StatesGroup):
    waiting_for_network = State()
    waiting_for_file_request = State()

class MonitoringState(StatesGroup):
    waiting_for_interval = State()
    waiting_for_autostart = State()
    waiting_for_notify_change = State()
    waiting_for_notify_start = State()

class NotificationState(StatesGroup):
    waiting_for_level = State()
    waiting_for_quiet_toggle = State()
    waiting_for_toggle = State()

class ScanSettingsState(StatesGroup):
    waiting_for_timeout = State()
    waiting_for_max_concurrent = State()
    waiting_for_default_ports = State()
    waiting_for_miner_ports = State()
    waiting_for_router_ports = State()
    waiting_for_ttl = State()

class RouterSettingsState(StatesGroup):
    waiting_for_ips = State()
    waiting_for_ports = State()
    waiting_for_interval = State()

class InterfaceSettingsState(StatesGroup):
    waiting_for_language = State()
    waiting_for_progress = State()
    waiting_for_time = State()
    waiting_for_compact = State()

class SecuritySettingsState(StatesGroup):
    waiting_for_users = State()
    waiting_for_log_level = State()
    waiting_for_token = State()
    waiting_for_access_control = State()

class BackupSettingsState(StatesGroup):
    waiting_for_interval = State()
    waiting_for_max_count = State()
    waiting_for_import = State()
    waiting_for_auto = State()

class SnmpRouterSettingsState(StatesGroup):
    waiting_for_community = State()

class SnmpRouterExtendedState(StatesGroup):
    waiting_for_router = State()

class AsicSettingsState(StatesGroup):
    waiting_for_ips = State()

# --- Universal menu button filter ---
def is_menu_button(key):
    def inner(m):
        lang = get_lang(m)
        btn_text = translate(lang, key)
        result = m.text == btn_text or m.text == key
        # Логируем для отладки
        print(f"[is_menu_button] key={key!r}, lang={lang!r}, btn_text={btn_text!r}, m.text={m.text!r}, result={result}")
        return result
    return inner

def get_user_role(message: Message) -> str:
    """Определяет роль пользователя: admin, operator, none"""
    user_id = message.from_user.id
    return settings_manager.get_user_role(user_id)

def check_user_access(message: Message) -> bool:
    """Проверяет, является ли пользователь оператором или админом"""
    role = get_user_role(message)
    return role in ('admin', 'operator')

def check_admin(message: Message) -> bool:
    """Проверяет, является ли пользователь админом"""
    return get_user_role(message) == 'admin'

def check_operator_or_admin(message: Message) -> bool:
    """Проверяет, является ли пользователь оператором или админом"""
    return get_user_role(message) in ('admin', 'operator')

async def send_access_denied(message: Message):
    """Отправляет сообщение об отказе в доступе"""
    await message.answer(
        translate(get_lang(message), 'access_denied'),
        reply_markup=ReplyKeyboardRemove()
    )

async def send_admin_only(message: Message):
    await message.answer(translate(get_lang(message), 'admin_only'), reply_markup=ReplyKeyboardRemove())

@dp.message_handler(commands=['start', 'menu'])
async def send_welcome(message: Message):
    # Проверяем доступ пользователя
    if not check_user_access(message):
        await send_access_denied(message)
        return
    statistics_manager.record_command('start')
    role = get_user_role(message)
    lang = get_lang(message)
    await message.answer(
        translate(lang, 'welcome'),
        reply_markup=main_menu_keyboard(lang=lang, role=role)
    )

@dp.message_handler(is_menu_button('status_main_menu_btn'))
async def handle_status_main_menu(message: Message):
    # Проверяем доступ пользователя
    if not check_user_access(message):
        await send_access_denied(message)
        return
    
    await handle_status(message)

@dp.message_handler(is_menu_button('router_status_main_menu_btn'))
async def handle_router_status_main_menu(message: Message):
    # Проверяем доступ пользователя
    if not check_user_access(message):
        await send_access_denied(message)
        return
    
    await handle_router_status(message)

@dp.message_handler(is_menu_button('scan_main_menu_btn'))
async def handle_scan_main_menu(message: Message):
    if not check_user_access(message):
        await send_access_denied(message)
        return
    lang = get_lang(message)
    await message.answer(translate(lang, 'scan_main_menu_msg'), reply_markup=scan_main_menu_keyboard(lang=lang))

@dp.message_handler(is_menu_button('settings_main_menu_btn'), state='*')
async def handle_settings_main_menu_btn(message: Message, state: FSMContext):
    # Проверяем доступ пользователя
    if not check_user_access(message):
        await send_access_denied(message)
        return
    await state.finish()
    lang = get_lang(message)
    await message.answer(translate(lang, 'settings_menu_msg'), reply_markup=settings_main_menu_keyboard(lang=lang, role=get_user_role(message)))

@dp.message_handler(is_menu_button('scan_network_main_menu_btn'))
async def handle_scan_network_main_menu(message: Message, state: FSMContext):
    if not check_user_access(message):
        await send_access_denied(message)
        return
    lang = get_lang(message)
    await message.answer(
        translate(lang, 'scan_network_prompt'),
        reply_markup=scan_cancel_or_main_keyboard(lang=lang)
    )
    await ScanDevicesState.waiting_for_network.set()

@dp.message_handler(is_menu_button('scan_miners_main_menu_btn'))
async def handle_scan_miners_main_menu(message: Message, state: FSMContext):
    if not check_user_access(message):
        await send_access_denied(message)
        return
    lang = get_lang(message)
    await message.answer(
        translate(lang, 'scan_miners_prompt'),
        reply_markup=scan_cancel_or_main_keyboard(lang=lang)
    )
    await ScanMinersState.waiting_for_network.set()

@dp.message_handler(is_menu_button('fast_scan_main_menu_btn'))
async def handle_fast_scan_main_menu(message: Message, state: FSMContext):
    if not check_user_access(message):
        await send_access_denied(message)
        return
    await message.answer(
        translate(get_lang(message), 'fast_scan_prompt'),
        reply_markup=scan_cancel_or_main_keyboard(lang=get_lang(message))
    )
    await FastScanState.waiting_for_network.set()

@dp.message_handler(is_menu_button('upload_file_main_menu_btn'))
async def handle_upload_file_main_menu(message: Message):
    # Проверяем доступ пользователя
    if not check_user_access(message):
        await send_access_denied(message)
        return
    
    await handle_upload_file(message)

@dp.message_handler(is_menu_button('backup_main_menu_btn'))
async def handle_backup_main_menu(message: Message):
    if not check_user_access(message):
        await send_access_denied(message)
        return
    lang = get_lang(message)
    await message.answer(translate(lang, 'backup_menu_msg'), reply_markup=backup_menu_keyboard(lang=lang))

@dp.message_handler(is_menu_button('export_main_menu_btn'))
async def handle_export_main_menu(message: Message):
    if not check_user_access(message):
        await send_access_denied(message)
        return
    lang = get_lang(message)
    await message.answer(translate(lang, 'export_menu_msg'), reply_markup=export_menu_keyboard(lang=lang))

@dp.message_handler(is_menu_button('monitoring_settings_btn'))
async def handle_monitoring_settings(message: Message):
    lang = get_lang(message)
    await message.answer(translate(lang, 'monitoring_menu_msg'), reply_markup=monitoring_menu_keyboard(lang=lang))

@dp.message_handler(is_menu_button('scan_settings_btn'))
async def handle_scan_settings(message: Message):
    lang = get_lang(message)
    await message.answer("SETTINGS HANDLER")
    await message.answer(translate(lang, 'scan_menu_msg'), reply_markup=scan_menu_keyboard(lang=lang))

@dp.message_handler(is_menu_button('notification_settings_btn'))
async def handle_notification_settings(message: Message):
    lang = get_lang(message)
    await message.answer(translate(lang, 'notification_menu_msg'), reply_markup=notification_menu_keyboard(lang=lang))

@dp.message_handler(is_menu_button('router_settings_btn'))
async def handle_router_settings(message: Message):
    lang = get_lang(message)
    await message.answer(translate(lang, 'router_menu_msg'), reply_markup=router_menu_keyboard(lang=lang))

@dp.message_handler(is_menu_button('interface_settings_btn'))
async def handle_interface_settings(message: Message):
    lang = get_lang(message)
    role = get_user_role(message)
    await message.answer(translate(lang, 'interface_menu_msg'), reply_markup=interface_menu_keyboard(lang=lang, role=role))

@dp.message_handler(is_menu_button('security_settings_btn'))
async def handle_security_settings(message: Message):
    lang = get_lang(message)
    await message.answer(translate(lang, 'security_menu_msg'), reply_markup=security_menu_keyboard(lang=lang))

@dp.message_handler(is_menu_button('help_main_menu_btn'))
async def handle_help_main_menu(message: Message):
    if not check_user_access(message):
        await send_access_denied(message)
        return
    statistics_manager.record_command('help')
    help_text = help_system.get_main_help()
    lang = get_lang(message)
    await message.answer(help_text, parse_mode='Markdown', reply_markup=help_menu_keyboard(lang=lang))

@dp.message_handler(is_menu_button('back_to_main_btn'), state=[ScanDevicesState.waiting_for_network, ScanMinersState.waiting_for_network, FastScanState.waiting_for_network])
async def scan_back_to_main(message: Message, state: FSMContext):
    await state.finish()
    lang = get_lang(message)
    role = get_user_role(message)
    await message.answer(
        translate(lang, 'main_menu'),
        reply_markup=main_menu_keyboard(lang=lang, role=role)
    )

@dp.message_handler(commands=['help'])
async def handle_help_command(message: Message):
    # Проверяем доступ пользователя
    if not check_user_access(message):
        await send_access_denied(message)
        return
    
    statistics_manager.record_command('help')
    help_text = help_system.get_main_help()
    await message.answer(
        help_text,
        parse_mode='Markdown',
        reply_markup=help_menu_keyboard(lang=get_lang(message))
    )

@dp.message_handler(commands=['status'])
async def handle_status(message: Message):
    # Проверяем доступ пользователя
    if not check_user_access(message):
        await send_access_denied(message)
        return
    
    statistics_manager.record_command('status')
    active_results = scan_manager.get_results_count()
    active_scans = scan_manager.get_active_count()
    total_routers = len(ROUTER_IPS)
    monitor_status = "🟢 Активен" if background_monitor.is_running else "🔴 Остановлен"
    status_text = f"""
🤖 *Статус бота:*
📊 Активных результатов сканирования: `{active_results}`
🔄 Сканирований в процессе: `{active_scans}`
🌐 Роутеров в мониторинге: `{total_routers}`
📡 Мониторинг: {monitor_status}
⏰ TTL результатов: `{scan_manager._ttl}` сек
🟢 Бот работает: ✅
    """
    await message.answer(status_text, parse_mode='Markdown')

@dp.message_handler(commands=['stats'])
async def handle_stats_command(message: Message):
    # Проверяем доступ пользователя
    if not check_user_access(message):
        await send_access_denied(message)
        return
    
    statistics_manager.record_command('stats')
    report = statistics_manager.generate_report()
    await message.answer(report, parse_mode='Markdown')

@dp.message_handler(commands=['monitor_start'])
async def handle_monitor_start(message: Message):
    # Проверяем доступ пользователя
    if not check_user_access(message):
        await send_access_denied(message)
        return
    
    statistics_manager.record_command('monitor_start')
    await background_monitor.start_monitoring()
    await notification_manager.send_notification(
        level=NotificationLevel.SUCCESS,
        notification_type=NotificationType.SYSTEM_ALERT,
        title="Мониторинг запущен",
        message="Фоновый мониторинг роутеров успешно запущен"
    )
    await message.answer(translate(get_lang(message), 'monitor_start_success'))

@dp.message_handler(commands=['monitor_stop'])
async def handle_monitor_stop(message: Message):
    # Проверяем доступ пользователя
    if not check_user_access(message):
        await send_access_denied(message)
        return
    
    statistics_manager.record_command('monitor_stop')
    await background_monitor.stop_monitoring()
    await notification_manager.send_notification(
        level=NotificationLevel.INFO,
        notification_type=NotificationType.SYSTEM_ALERT,
        title="Мониторинг остановлен",
        message="Фоновый мониторинг роутеров остановлен"
    )
    await message.answer(translate(get_lang(message), 'monitor_stop_success'))

async def send_notify_to_owner(text: str):
    await bot.send_message(CHAT_ID, text)

async def on_startup(dp):
    """Функция, выполняемая при запуске бота"""
    logging.info("[STARTUP] Запуск бота...")
    
    # Запускаем систему уведомлений
    await notification_manager.start()
    
    # Автозапуск мониторинга, если включено в настройках
    if settings_manager.get_setting('monitoring.auto_start', True):
        interval = settings_manager.get_setting('monitoring.interval', 300)
        await background_monitor.start_monitoring(interval)
    
    # Отправляем уведомление о запуске
    await notification_manager.send_notification(
        level=NotificationLevel.INFO,
        notification_type=NotificationType.SYSTEM_ALERT,
        title="Бот запущен",
        message="Система мониторинга и сканирования готова к работе"
    )
    
    logging.info("[STARTUP] Бот успешно запущен")

async def on_shutdown(dp):
    """Функция, выполняемая при остановке бота"""
    logging.info("[SHUTDOWN] Остановка бота...")
    
    # Останавливаем мониторинг
    await background_monitor.stop_monitoring()
    
    # Останавливаем систему уведомлений
    await notification_manager.stop()
    
    # Отправляем уведомление об остановке
    try:
        await notification_manager.send_notification(
            level=NotificationLevel.WARNING,
            notification_type=NotificationType.SYSTEM_ALERT,
            title="Бот остановлен",
            message="Система мониторинга остановлена"
        )
    except:
        pass
    
    logging.info("[SHUTDOWN] Бот остановлен")

@dp.message_handler(state=ScanDevicesState.waiting_for_timeout)
async def process_timeout_input(message: Message, state: FSMContext):
    try:
        timeout = int(message.text.strip())
        if timeout < 1 or timeout > 60:
            await message.answer(translate(get_lang(message), 'timeout_error'))
            return
        if settings_manager.set_setting('scanning.default_timeout', timeout):
            await message.answer(translate(get_lang(message), 'timeout_set', timeout=timeout))
        else:
            await message.answer(translate(get_lang(message), 'timeout_save_error'))
    except Exception:
        await message.answer(translate(get_lang(message), 'timeout_input_error'))
    await state.finish()

@dp.message_handler(lambda m: m.text == 'Статус роутеров')
async def handle_router_status(message: Message):
    statistics_manager.record_command('status_routers')
    lang = get_lang(message)
    role = get_user_role(message)
    await message.answer(translate(lang, 'checking_routers'))
    ips = settings_manager.get_setting('routers.ips', [])
    ports = settings_manager.get_setting('routers.ports', [8080, 80, 22])
    results = await check_routers_status(ips, ports)
    online_count = sum(1 for r in results if r['status'] == 'online')
    statistics_manager.record_router_check(online_count, len(ips))
    text = "🌐 *Статус роутеров:*\n\n"
    for r in results:
        emoji = "🟢" if r['status'] == 'online' else "🔴"
        text += f"{emoji} *{r['ip']}*: {r['status']}\n"
        if r['open_ports']:
            text += f"   📡 Порт(ы): {', '.join(map(str, r['open_ports']))}\n"
        text += "\n"
    await message.answer(text, parse_mode='Markdown', reply_markup=main_menu_keyboard(lang=lang, role=role))

@dp.message_handler(lambda m: m.text == 'Сканировать сеть')
async def handle_scan_network(message: Message):
    statistics_manager.record_command('scan_network')
    await message.answer(translate(get_lang(message), 'scan_network_prompt'), reply_markup=scan_menu_keyboard(lang=get_lang(message)))
    await ScanDevicesState.waiting_for_network.set()

@dp.message_handler(state=ScanDevicesState.waiting_for_network)
async def process_devices_network_input(message: Message, state: FSMContext):
    import logging
    cleanup_old_results()
    scan_manager.start_scan()
    network = message.text.strip()
    start_time = time.time()
    logging.info(f"[SCAN_NETWORK] Пользователь {message.from_user.id} ввёл сеть: {network}")
    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except Exception as e:
        logging.error(f"[SCAN_NETWORK] Некорректная сеть: {network}, ошибка: {e}")
        await message.answer(translate(get_lang(message), 'network_format_error'), reply_markup=main_menu_keyboard(lang=get_lang(message)))
        scan_manager.finish_scan()
        await state.finish()
        return
    progress_msg = await message.answer(translate(get_lang(message), 'scanning_network', network=network))
    async def on_progress(done, total):
        percent = int(done / total * 100)
        bar = '█' * (percent // 10) + '-' * (10 - percent // 10)
        await bot.edit_message_text(
            translate(get_lang(message), 'scanning_progress', bar=bar, percent=percent, done=done, total=total),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
    try:
        logging.info(f"[SCAN_NETWORK] Запуск scan_network_devices для {network}")
        devices = await scan_network_devices(network, on_progress=on_progress)
        duration = time.time() - start_time
        logging.info(f"[SCAN_NETWORK] Завершено scan_network_devices для {network}, найдено устройств: {len(devices)} за {duration:.1f}с")
        await bot.edit_message_text(
            translate(get_lang(message), 'scan_completed', count=len(devices)),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        statistics_manager.record_scan('network', len(devices), net.num_addresses, duration)
        await notification_manager.scan_completed('сети', len(devices), duration)
        if not devices:
            await message.answer(translate(get_lang(message), 'no_devices_found'), reply_markup=main_menu_keyboard(lang=get_lang(message)))
            scan_manager.finish_scan()
            await state.finish()
            return
        text = f"Найдено устройств: {len(devices)}\n"
        for d in devices:
            if d.get('type') == 'miner':
                text += f"{d['ip']}: miner (hashrate: {d.get('hashrate')}, uptime: {d.get('uptime')})\n"
            else:
                text += f"{d['ip']}: (открытые порты: {', '.join(map(str, d['open_ports']))})\n"
        text += "\nЕсли хотите получить файл с результатами, напишите 'файл' в ответ или reply на это сообщение."
        scan_manager.save_scan_result('scan', network, {'devices': devices, 'type': 'devices', 'timestamp': time.time()})
        if len(text) > 4000:
            file_path = scan_manager.get_scan_result_file('scan', network, ext='csv')
            if file_path:
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton(text=translate(get_lang(message), 'get_ip_list_btn'), callback_data=f'get_ips_file:{file_path}'))
                await message.answer_document(open(file_path, 'rb'), caption=translate(get_lang(message), 'scan_file_sent'), reply_markup=kb)
            else:
                await message.answer(translate(get_lang(message), 'scan_file_not_found'), reply_markup=main_menu_keyboard(lang=get_lang(message)))
        else:
            result_msg = await message.answer(text, reply_markup=main_menu_keyboard(lang=get_lang(message)))
            scan_manager.add_result(result_msg.message_id, {
                'devices': devices,
                'type': 'devices',
                'timestamp': time.time(),
                'network': network
            })
            await ScanDevicesState.waiting_for_file_request.set()
        scan_manager.finish_scan()
        await state.finish()
    except Exception as e:
        logging.exception(f"[SCAN_NETWORK] Ошибка при сканировании {network}: {e}")
        await bot.edit_message_text(
            translate(get_lang(message), 'scan_error', e=e),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        await message.answer(f"[SCAN_NETWORK] Произошла ошибка: {e}", reply_markup=main_menu_keyboard(lang=get_lang(message)))
        scan_manager.finish_scan()
        await state.finish()

@dp.message_handler(lambda m: m.text == 'Загрузить файл для сканирования')
async def handle_upload_file(message: Message):
    statistics_manager.record_command('upload_file')
    await message.answer(translate(get_lang(message), 'upload_file_prompt'), reply_markup=main_menu_keyboard(lang=get_lang(message)))

@dp.message_handler(content_types=ContentType.DOCUMENT)
async def process_csv_file(message: Message):
    file = message.document
    if not file.file_name.lower().endswith('.csv'):
        await message.answer(translate(get_lang(message), 'csv_format_error'), reply_markup=main_menu_keyboard(lang=get_lang(message)))
        return
    file_path = os.path.join(BASE_DIR, file.file_name)
    await message.document.download(destination_file=file_path)
    try:
        df = pd.read_csv(file_path)
        if 'ip' not in df.columns:
            await message.answer(translate(get_lang(message), 'ip_column_error'), reply_markup=main_menu_keyboard(lang=get_lang(message)))
            return
        ip_list = df['ip'].dropna().astype(str).tolist()
        await message.answer(
            translate(get_lang(message), 'scanning_ips', count=len(ip_list)),
            reply_markup=main_menu_keyboard(lang=get_lang(message))
        )
        start_time = time.time()
        miners = await scan_miners_from_list(ip_list)
        duration = time.time() - start_time
        statistics_manager.record_scan('file_upload', len(miners), len(ip_list), duration)
        if not miners:
            await message.answer(translate(get_lang(message), 'no_miners_found'), reply_markup=main_menu_keyboard(lang=get_lang(message)))
        else:
            text = "Результаты сканирования:\n"
            for m in miners:
                text += f"{m['ip']}: status={m['status']}, hashrate={m['hashrate']}, uptime={m['uptime']}\n"
            await message.answer(text, reply_markup=main_menu_keyboard(lang=get_lang(message)))
    except Exception as e:
        statistics_manager.record_error('file_processing', str(e))
        await message.answer(translate(get_lang(message), 'file_processing_error', e=e), reply_markup=main_menu_keyboard(lang=get_lang(message)))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@dp.message_handler(lambda m: m.text == 'Сканировать майнеры')
async def handle_scan_miners(message: Message):
    statistics_manager.record_command('scan_miners')
    await message.answer(translate(get_lang(message), 'scan_miners_prompt'), reply_markup=scan_menu_keyboard(lang=get_lang(message)))
    await ScanMinersState.waiting_for_network.set()

@dp.message_handler(state=ScanMinersState.waiting_for_network)
async def process_miners_network_input(message: Message, state: FSMContext):
    import logging
    cleanup_old_results()
    scan_manager.start_scan()
    network = message.text.strip()
    logging.info(f"[SCAN_MINERS] Пользователь {message.from_user.id} ввёл сеть: {network}")
    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except Exception as e:
        logging.error(f"[SCAN_MINERS] Некорректная сеть: {network}, ошибка: {e}")
        await message.answer(translate(get_lang(message), 'network_format_error'), reply_markup=main_menu_keyboard(lang=get_lang(message)))
        scan_manager.finish_scan()
        await state.finish()
        return
    progress_msg = await message.answer(translate(get_lang(message), 'scanning_miners', network=network))
    async def on_progress(done, total):
        percent = int(done / total * 100)
        bar = '█' * (percent // 10) + '-' * (10 - percent // 10)
        await bot.edit_message_text(
            translate(get_lang(message), 'miners_scanning_progress', bar=bar, percent=percent, done=done, total=total),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
    try:
        logging.info(f"[SCAN_MINERS] Запуск scan_network_for_miners для {network}")
        miners = await scan_network_for_miners(network, on_progress=on_progress)
        logging.info(f"[SCAN_MINERS] Завершено scan_network_for_miners для {network}, найдено майнеров: {len(miners)}")
        await bot.edit_message_text(
            translate(get_lang(message), 'scan_completed', count=len(miners)),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        if not miners:
            await message.answer(translate(get_lang(message), 'no_miners_found'), reply_markup=main_menu_keyboard(lang=get_lang(message)))
            scan_manager.finish_scan()
            await state.finish()
            return
        text = f"Сканирование сети: {network}\n"
        text += "Найдено майнеров: {}\n".format(len(miners))
        for m in miners:
            text += f"{m['ip']}: miner (hashrate: {m.get('hashrate')}, uptime: {m.get('uptime')})\n"
        text += "\nЕсли хотите получить файл с результатами, напишите 'файл' в ответ или reply на это сообщение."
        scan_manager.save_scan_result('miners', network, {'miners': miners, 'type': 'miners', 'timestamp': time.time()})
        if len(text) > 4000:
            file_path = scan_manager.get_scan_result_file('miners', network, ext='csv')
            if file_path:
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton(text=translate(get_lang(message), 'get_ip_list_btn'), callback_data=f'get_ips_file:{file_path}'))
                await message.answer_document(open(file_path, 'rb'), caption=translate(get_lang(message), 'scan_file_sent'), reply_markup=kb)
            else:
                await message.answer(translate(get_lang(message), 'scan_file_not_found'), reply_markup=main_menu_keyboard(lang=get_lang(message)))
        else:
            result_msg = await message.answer(text, reply_markup=main_menu_keyboard(lang=get_lang(message)))
            scan_manager.add_result(result_msg.message_id, {
                'miners': miners,
                'type': 'miners',
                'timestamp': time.time(),
                'network': network
            })
            await ScanMinersState.waiting_for_file_request.set()
        scan_manager.finish_scan()
        await state.finish()
    except Exception as e:
        logging.exception(f"[SCAN_MINERS] Ошибка при сканировании {network}: {e}")
        await bot.edit_message_text(
            translate(get_lang(message), 'scan_error', e=e),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        await message.answer(f"[SCAN_MINERS] Произошла ошибка: {e}", reply_markup=main_menu_keyboard(lang=get_lang(message)))
        scan_manager.finish_scan()
        await state.finish()

@dp.message_handler(lambda m: m.text == 'Быстрое сканирование сети')
async def handle_fast_scan(message: Message):
    await message.answer(translate(get_lang(message), 'fast_scan_prompt'), reply_markup=scan_menu_keyboard(lang=get_lang(message)))
    await FastScanState.waiting_for_network.set()

@dp.message_handler(state=FastScanState.waiting_for_network)
async def process_fast_scan_network_input(message: Message, state: FSMContext):
    import logging
    cleanup_old_results()
    scan_manager.start_scan()
    network = message.text.strip()
    logging.info(f"[FAST_SCAN] Пользователь {message.from_user.id} ввёл сеть: {network}")
    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except Exception as e:
        logging.error(f"[FAST_SCAN] Некорректная сеть: {network}, ошибка: {e}")
        await message.answer(translate(get_lang(message), 'network_format_error'), reply_markup=main_menu_keyboard(lang=get_lang(message)))
        scan_manager.finish_scan()
        await state.finish()
        return
    progress_msg = await message.answer(translate(get_lang(message), 'fast_scanning', network=network))
    async def on_progress(done, total):
        percent = int(done / total * 100)
        bar = '█' * (percent // 10) + '-' * (10 - percent // 10)
        await bot.edit_message_text(
            translate(get_lang(message), 'fast_scanning_progress', bar=bar, percent=percent, done=done, total=total),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
    try:
        logging.info(f"[FAST_SCAN] Запуск fast_scan_network для {network}")
        devices = await fast_scan_network(network, on_progress=on_progress)
        logging.info(f"[FAST_SCAN] Завершено fast_scan_network для {network}, найдено устройств: {len(devices)}")
        await bot.edit_message_text(
            translate(get_lang(message), 'fast_scan_completed', count=len(devices)),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        if not devices:
            await message.answer(translate(get_lang(message), 'no_devices_found'), reply_markup=main_menu_keyboard(lang=get_lang(message)))
            scan_manager.finish_scan()
            await state.finish()
            return
        text = f"Сканирование сети: {network}\n"
        text += "Найдено устройств: {}\n".format(len(devices))
        for d in devices:
            if d.get('type') == 'miner':
                text += f"{d['ip']}: miner (hashrate: {d.get('hashrate')}, uptime: {d.get('uptime')})\n"
            else:
                text += f"{d['ip']}: {d.get('type', 'unknown')} (открытые порты: {', '.join(map(str, d['open_ports']))})\n"
        text += "\nЕсли хотите получить файл с результатами, напишите 'файл' в ответ или reply на это сообщение."
        scan_manager.save_scan_result('fast_scan', network, {'devices': devices, 'type': 'fast_scan', 'timestamp': time.time()})
        if len(text) > 4000:
            file_path = scan_manager.get_scan_result_file('fast_scan', network, ext='csv')
            if file_path:
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton(text=translate(get_lang(message), 'get_ip_list_btn'), callback_data=f'get_ips_file:{file_path}'))
                await message.answer_document(open(file_path, 'rb'), caption=translate(get_lang(message), 'scan_file_sent'), reply_markup=kb)
            else:
                await message.answer(translate(get_lang(message), 'scan_file_not_found'), reply_markup=main_menu_keyboard(lang=get_lang(message)))
        else:
            result_msg = await message.answer(text, reply_markup=main_menu_keyboard(lang=get_lang(message)))
            scan_manager.add_result(result_msg.message_id, {
                'fast_scan': devices,
                'type': 'fast_scan',
                'timestamp': time.time(),
                'network': network
            })
            await FastScanState.waiting_for_file_request.set()
        scan_manager.finish_scan()
        await state.finish()
    except Exception as e:
        logging.exception(f"[FAST_SCAN] Ошибка при сканировании {network}: {e}")
        await bot.edit_message_text(
            translate(get_lang(message), 'fast_scan_error', e=e),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        await message.answer(f"[FAST_SCAN] Произошла ошибка: {e}", reply_markup=main_menu_keyboard(lang=get_lang(message)))
        scan_manager.finish_scan()
        await state.finish()

@dp.message_handler(lambda m: m.text == 'Статистика')
async def handle_statistics(message: Message):
    # Проверяем доступ пользователя
    if not check_user_access(message):
        await send_access_denied(message)
        return
    
    # Информация из /status
    active_results = scan_manager.get_results_count()
    active_scans = scan_manager.get_active_count()
    total_routers = len(ROUTER_IPS)
    monitor_status = "🟢 Активен" if background_monitor.is_running else "🔴 Остановлен"
    status_text = f"""
🤖 *Статус бота:*
📊 Активных результатов сканирования: `{active_results}`
🔄 Сканирований в процессе: `{active_scans}`
🌐 Роутеров в мониторинге: `{total_routers}`
📡 Мониторинг: {monitor_status}
⏰ TTL результатов: `{scan_manager._ttl}` сек
🟢 Бот работает: ✅
"""
    report = statistics_manager.generate_report()
    await message.answer(status_text, parse_mode='Markdown')
    await message.answer(report, parse_mode='Markdown', reply_markup=main_menu_keyboard(lang=get_lang(message)))

@dp.message_handler(is_menu_button('monitoring_interval_btn'))
async def handle_monitoring_interval(message: Message):
    current = settings_manager.get_setting('monitoring.interval', 300)
    lang = get_lang(message)
    await message.answer(translate(lang, 'monitoring_interval_prompt', value=current), reply_markup=cancel_keyboard(lang=lang))
    await MonitoringState.waiting_for_interval.set()

@dp.message_handler(state=MonitoringState.waiting_for_interval)
async def process_monitoring_interval(message: Message, state: FSMContext):
    lang = get_lang(message)
    try:
        interval = int(message.text.strip())
        if interval < 10 or interval > 86400:
            await message.answer(translate(lang, 'monitoring_interval_error'), reply_markup=monitoring_menu_keyboard(lang=lang))
            return
        if settings_manager.set_setting('monitoring.interval', interval):
            await message.answer(translate(lang, 'monitoring_interval_set', value=interval), reply_markup=monitoring_menu_keyboard(lang=lang))
        else:
            await message.answer(translate(lang, 'monitoring_interval_save_error'), reply_markup=monitoring_menu_keyboard(lang=lang))
    except Exception:
        await message.answer(translate(lang, 'monitoring_interval_input_error'), reply_markup=monitoring_menu_keyboard(lang=lang))
    await state.finish()

@dp.message_handler(is_menu_button('monitoring_autostart_btn'))
async def handle_monitoring_autostart(message: Message):
    current = settings_manager.get_setting('monitoring.auto_start', True)
    value = 'да' if current else 'нет'
    lang = get_lang(message)
    await message.answer(translate(lang, 'monitoring_autostart_prompt', value=value), reply_markup=cancel_keyboard(lang=lang))
    await MonitoringState.waiting_for_autostart.set()

@dp.message_handler(state=MonitoringState.waiting_for_autostart)
async def process_monitoring_autostart(message: Message, state: FSMContext):
    lang = get_lang(message)
    text = message.text.strip().lower()
    if text in ['да', 'yes', 'y', 'oui', 'ja', '是']:
        new_value = True
    elif text in ['нет', 'no', 'n', 'non', 'nein', '否']:
        new_value = False
    else:
        await message.answer(translate(lang, 'input_error'), reply_markup=monitoring_menu_keyboard(lang=lang))
        await state.finish()
        return
    if settings_manager.set_setting('monitoring.auto_start', new_value):
        status = 'включён' if new_value else 'выключен'
        await message.answer(translate(lang, 'monitoring_autostart_set', status=status), reply_markup=monitoring_menu_keyboard(lang=lang))
    else:
        await message.answer(translate(lang, 'settings_error'), reply_markup=monitoring_menu_keyboard(lang=lang))
    await state.finish()

@dp.message_handler(is_menu_button('monitoring_notify_change_btn'))
async def handle_monitoring_notify_change(message: Message):
    current = settings_manager.get_setting('monitoring.notify_on_change', True)
    value = 'да' if current else 'нет'
    lang = get_lang(message)
    await message.answer(translate(lang, 'monitoring_notify_change_prompt', value=value), reply_markup=cancel_keyboard(lang=lang))
    await MonitoringState.waiting_for_notify_change.set()

@dp.message_handler(state=MonitoringState.waiting_for_notify_change)
async def process_monitoring_notify_change(message: Message, state: FSMContext):
    lang = get_lang(message)
    text = message.text.strip().lower()
    if text in ['да', 'yes', 'y', 'oui', 'ja', '是']:
        new_value = True
    elif text in ['нет', 'no', 'n', 'non', 'nein', '否']:
        new_value = False
    else:
        await message.answer(translate(lang, 'input_error'), reply_markup=monitoring_menu_keyboard(lang=lang))
        await state.finish()
        return
    if settings_manager.set_setting('monitoring.notify_on_change', new_value):
        status = 'включены' if new_value else 'выключены'
        await message.answer(translate(lang, 'monitoring_notify_change_set', status=status), reply_markup=monitoring_menu_keyboard(lang=lang))
    else:
        await message.answer(translate(lang, 'settings_error'), reply_markup=monitoring_menu_keyboard(lang=lang))
    await state.finish()

@dp.message_handler(is_menu_button('monitoring_notify_start_btn'))
async def handle_monitoring_notify_start(message: Message):
    current = settings_manager.get_setting('monitoring.notify_on_start', True)
    value = 'да' if current else 'нет'
    lang = get_lang(message)
    await message.answer(translate(lang, 'monitoring_notify_start_prompt', value=value), reply_markup=cancel_keyboard(lang=lang))
    await MonitoringState.waiting_for_notify_start.set()

@dp.message_handler(state=MonitoringState.waiting_for_notify_start)
async def process_monitoring_notify_start(message: Message, state: FSMContext):
    lang = get_lang(message)
    text = message.text.strip().lower()
    if text in ['да', 'yes', 'y', 'oui', 'ja', '是']:
        new_value = True
    elif text in ['нет', 'no', 'n', 'non', 'nein', '否']:
        new_value = False
    else:
        await message.answer(translate(lang, 'input_error'), reply_markup=monitoring_menu_keyboard(lang=lang))
        await state.finish()
        return
    if settings_manager.set_setting('monitoring.notify_on_start', new_value):
        status = 'включены' if new_value else 'выключены'
        await message.answer(translate(lang, 'monitoring_notify_start_set', status=status), reply_markup=monitoring_menu_keyboard(lang=lang))
    else:
        await message.answer(translate(lang, 'settings_error'), reply_markup=monitoring_menu_keyboard(lang=lang))
    await state.finish()

@dp.message_handler(is_menu_button('scan_timeout_btn'))
async def handle_scan_timeout(message: Message):
    current = settings_manager.get_setting('scanning.default_timeout', 5)
    lang = get_lang(message)
    await message.answer(translate(lang, 'scan_timeout_prompt', value=current), reply_markup=cancel_keyboard(lang=lang))
    await ScanSettingsState.waiting_for_timeout.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_timeout)
async def process_scan_timeout(message: Message, state: FSMContext):
    try:
        timeout = int(message.text.strip())
        if timeout < 1 or timeout > 60:
            await message.answer(translate(get_lang(message), 'scan_timeout_error'))
            return
        if settings_manager.set_setting('scanning.default_timeout', timeout):
            await message.answer(translate(get_lang(message), 'scan_timeout_set', value=timeout))
        else:
            await message.answer(translate(get_lang(message), 'scan_timeout_save_error'))
    except Exception:
        await message.answer(translate(get_lang(message), 'scan_timeout_input_error'))
    await state.finish()

@dp.message_handler(is_menu_button('scan_max_concurrent_btn'))
async def handle_scan_max_concurrent(message: Message):
    current = settings_manager.get_setting('scanning.max_concurrent_scans', 3)
    await message.answer(translate(get_lang(message), 'scan_max_concurrent_prompt', value=current), reply_markup=cancel_keyboard(lang=get_lang(message)))
    await ScanSettingsState.waiting_for_max_concurrent.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_max_concurrent)
async def process_scan_max_concurrent(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value < 1 or value > 20:
            await message.answer(translate(get_lang(message), 'scan_max_concurrent_error'))
            return
        if settings_manager.set_setting('scanning.max_concurrent_scans', value):
            await message.answer(translate(get_lang(message), 'scan_max_concurrent_set', value=value))
        else:
            await message.answer(translate(get_lang(message), 'scan_max_concurrent_save_error'))
    except Exception:
        await message.answer(translate(get_lang(message), 'scan_max_concurrent_input_error'))
    await state.finish()

@dp.message_handler(is_menu_button('scan_ports_btn'))
async def handle_scan_ports(message: Message):
    current = settings_manager.get_setting('scanning.default_ports', [80, 22, 443])
    await message.answer(translate(get_lang(message), 'scan_ports_prompt', value=', '.join(map(str, current))), reply_markup=cancel_keyboard(lang=get_lang(message)))
    await ScanSettingsState.waiting_for_default_ports.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_default_ports)
async def process_scan_ports(message: Message, state: FSMContext):
    ports = parse_ports(message.text)
    if not ports:
        await message.answer(translate(get_lang(message), 'scan_ports_error'), reply_markup=scan_menu_keyboard(lang=get_lang(message)))
        await state.finish()
        return
    if settings_manager.set_setting('scanning.default_ports', ports):
        await message.answer(translate(get_lang(message), 'scan_ports_set', value=', '.join(map(str, ports))), reply_markup=scan_menu_keyboard(lang=get_lang(message)))
    else:
        await message.answer(translate(get_lang(message), 'scan_ports_save_error'), reply_markup=scan_menu_keyboard(lang=get_lang(message)))
    await state.finish()

@dp.message_handler(is_menu_button('scan_miner_ports_btn'))
async def handle_miner_ports(message: Message):
    current = settings_manager.get_setting('scanning.miner_ports', [4028, 3333])
    await message.answer(translate(get_lang(message), 'scan_miner_ports_prompt', value=', '.join(map(str, current))), reply_markup=cancel_keyboard(lang=get_lang(message)))
    await ScanSettingsState.waiting_for_miner_ports.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_miner_ports)
async def process_miner_ports(message: Message, state: FSMContext):
    ports = parse_ports(message.text)
    if not ports:
        await message.answer(translate(get_lang(message), 'scan_miner_ports_error'), reply_markup=scan_menu_keyboard(lang=get_lang(message)))
        await state.finish()
        return
    if settings_manager.set_setting('scanning.miner_ports', ports):
        await message.answer(translate(get_lang(message), 'scan_miner_ports_set', value=', '.join(map(str, ports))), reply_markup=scan_menu_keyboard(lang=get_lang(message)))
    else:
        await message.answer(translate(get_lang(message), 'scan_miner_ports_save_error'), reply_markup=scan_menu_keyboard(lang=get_lang(message)))
    await state.finish()

@dp.message_handler(is_menu_button('scan_router_ports_btn'))
async def handle_router_ports(message: Message):
    current = settings_manager.get_setting('scanning.router_ports', [8080, 80, 22])
    lang = get_lang(message)
    await message.answer(translate(lang, 'scan_router_ports_prompt', value=', '.join(map(str, current))), reply_markup=cancel_keyboard(lang=lang))
    await ScanSettingsState.waiting_for_router_ports.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_router_ports)
async def process_router_ports_settings(message: Message, state: FSMContext):
    ports = parse_ports(message.text)
    lang = get_lang(message)
    if not ports:
        await message.answer(translate(lang, 'scan_router_ports_error'), reply_markup=scan_menu_keyboard(lang=lang))
        await state.finish()
        return
    if settings_manager.set_setting('scanning.router_ports', ports):
        await message.answer(translate(lang, 'scan_router_ports_set', value=', '.join(map(str, ports))), reply_markup=scan_menu_keyboard(lang=lang))
    else:
        await message.answer(translate(lang, 'scan_router_ports_save_error'), reply_markup=scan_menu_keyboard(lang=lang))
    await state.finish()

@dp.message_handler(is_menu_button('scan_ttl_btn'))
async def handle_scan_ttl(message: Message):
    current = settings_manager.get_setting('scanning.results_ttl', 3600)
    lang = get_lang(message)
    await message.answer(translate(lang, 'scan_ttl_prompt', value=current), reply_markup=cancel_keyboard(lang=lang))
    await ScanSettingsState.waiting_for_ttl.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_ttl)
async def process_scan_ttl(message: Message, state: FSMContext):
    try:
        ttl = int(message.text.strip())
        if ttl < 60 or ttl > 604800:  # 7 дней
            await message.answer(translate(get_lang(message), 'scan_ttl_error'))
            return
        if settings_manager.set_setting('scanning.results_ttl', ttl):
            await message.answer(translate(get_lang(message), 'scan_ttl_set', value=ttl))
        else:
            await message.answer(translate(get_lang(message), 'scan_ttl_save_error'))
    except Exception:
        await message.answer(translate(get_lang(message), 'scan_ttl_input_error'))
    await state.finish()

def parse_ports(text):
    try:
        return [int(p.strip()) for p in text.split(',') if p.strip().isdigit()]
    except Exception:
        return []

@dp.message_handler(is_menu_button('notifications_toggle_btn'))
async def handle_toggle_notifications(message: Message):
    current = settings_manager.get_setting('notifications.enabled', True)
    value = 'да' if current else 'нет'
    lang = get_lang(message)
    await message.answer(translate(lang, 'notifications_toggle_prompt', value=value), reply_markup=cancel_keyboard(lang=lang))
    await NotificationState.waiting_for_toggle.set()

@dp.message_handler(is_menu_button('quiet_hours_btn'))
async def handle_toggle_quiet_hours(message: Message):
    current = settings_manager.get_setting('notifications.quiet_hours', {'start': '22:00', 'end': '08:00'})
    lang = get_lang(message)
    await message.answer(translate(lang, 'quiet_hours_current', start=current['start'], end=current['end']), reply_markup=cancel_keyboard(lang=lang))
    await NotificationState.waiting_for_quiet_toggle.set()

@dp.message_handler(is_menu_button('notifications_level_btn'))
async def handle_notification_level(message: Message):
    current = settings_manager.get_setting('notifications.level', 'INFO')
    lang = get_lang(message)
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('INFO'), KeyboardButton('WARNING'), KeyboardButton('ERROR'))
    keyboard.add(KeyboardButton(translate(lang, 'cancel')))
    await message.answer(translate(lang, 'notifications_level_current', value=current), reply_markup=keyboard)
    await NotificationState.waiting_for_level.set()

@dp.message_handler(is_menu_button('router_ips_btn'))
async def handle_router_ips(message: Message):
    current = settings_manager.get_setting('routers.ips', [])
    lang = get_lang(message)
    await message.answer(translate(lang, 'router_ips_prompt', value=', '.join(current)), reply_markup=cancel_keyboard(lang=lang))
    await RouterSettingsState.waiting_for_ips.set()

@dp.message_handler(state=RouterSettingsState.waiting_for_ips)
async def process_router_ips(message: Message, state: FSMContext):
    text = message.text.replace('\n', ',').replace(';', ',')
    ips = [ip.strip() for ip in text.split(',') if ip.strip()]
    if not all(validate_ip(ip) for ip in ips):
        await message.answer(translate(get_lang(message), 'scan_router_ips_error'), reply_markup=router_menu_keyboard(lang=get_lang(message)))
        await state.finish()
        return
    if settings_manager.update_router_ips(ips):
        await message.answer(translate(get_lang(message), 'scan_router_ips_set', value=', '.join(ips)), reply_markup=router_menu_keyboard(lang=get_lang(message)))
    else:
        await message.answer(translate(get_lang(message), 'scan_router_ips_save_error'), reply_markup=router_menu_keyboard(lang=get_lang(message)))
    await state.finish()

@dp.message_handler(is_menu_button('router_ports_btn'))
async def handle_router_ports_btn(message: Message):
    current = settings_manager.get_setting('routers.ports', [8080, 80, 22])
    lang = get_lang(message)
    await message.answer(translate(lang, 'router_ports_prompt', value=', '.join(map(str, current))), reply_markup=cancel_keyboard(lang=lang))
    await RouterSettingsState.waiting_for_ports.set()

@dp.message_handler(state=RouterSettingsState.waiting_for_ports)
async def process_router_ports(message: Message, state: FSMContext):
    ports = parse_ports(message.text)
    lang = get_lang(message)
    if not ports:
        await message.answer(translate(lang, 'scan_router_ports_error'), reply_markup=router_menu_keyboard(lang=lang))
        await state.finish()
        return
    if settings_manager.set_setting('routers.ports', ports):
        await message.answer(translate(lang, 'scan_router_ports_set', value=', '.join(map(str, ports))), reply_markup=router_menu_keyboard(lang=lang))
    else:
        await message.answer(translate(lang, 'scan_router_ports_save_error'), reply_markup=router_menu_keyboard(lang=lang))
    await state.finish()

@dp.message_handler(is_menu_button('router_interval_btn'))
async def handle_router_interval_btn(message: Message):
    current = settings_manager.get_setting('routers.interval', 300)
    lang = get_lang(message)
    await message.answer(translate(lang, 'router_interval_prompt', value=current), reply_markup=cancel_keyboard(lang=lang))
    await RouterSettingsState.waiting_for_interval.set()

@dp.message_handler(state=RouterSettingsState.waiting_for_interval)
async def process_router_interval(message: Message, state: FSMContext):
    try:
        interval = int(message.text.strip())
        if interval < 10 or interval > 86400:
            await message.answer(translate(get_lang(message), 'scan_router_interval_error'), reply_markup=router_menu_keyboard(lang=get_lang(message)))
            return
        if settings_manager.set_setting('routers.interval', interval):
            await message.answer(translate(get_lang(message), 'scan_router_interval_set', value=interval), reply_markup=router_menu_keyboard(lang=get_lang(message)))
        else:
            await message.answer(translate(get_lang(message), 'scan_router_interval_save_error'), reply_markup=router_menu_keyboard(lang=get_lang(message)))
    except Exception:
        await message.answer(translate(get_lang(message), 'scan_router_interval_input_error'), reply_markup=router_menu_keyboard(lang=get_lang(message)))
    await state.finish()

@dp.message_handler(is_menu_button('router_status_btn'))
async def handle_router_status_btn(message: Message):
    lang = get_lang(message)
    await message.answer(translate(lang, 'router_status_msg'), reply_markup=router_menu_keyboard(lang=lang))

def validate_ip(ip):
    import re
    return bool(re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', ip))

@dp.message_handler(is_menu_button('interface_language_btn'))
async def handle_interface_language(message: Message):
    current = get_lang(message)
    await message.answer(translate(current, 'interface_language_prompt', value=current), reply_markup=cancel_keyboard(lang=current))
    await InterfaceSettingsState.waiting_for_language.set()

@dp.message_handler(state=InterfaceSettingsState.waiting_for_language)
async def process_interface_language(message: Message, state: FSMContext):
    lang = message.text.strip().lower()
    if lang not in ['ru', 'en', 'de', 'nl', 'zh']:
        await message.answer(translate(get_lang(message), 'input_error'), reply_markup=interface_menu_keyboard(lang=get_lang(message), role=get_user_role(message)))
        await state.finish()
        return
    user_id = str(message.from_user.id)
    settings_manager.set_setting(f'user_languages.{user_id}', lang)
    await message.answer(translate(lang, 'interface_language_set', value=lang), reply_markup=main_menu_keyboard(lang=lang, role=get_user_role(message)))
    await state.finish()

@dp.message_handler(is_menu_button('interface_progress_btn'))
async def handle_interface_progress(message: Message):
    current = settings_manager.get_setting('interface.show_progress', True)
    value = 'да' if current else 'нет'
    lang = get_lang(message)
    await message.answer(translate(lang, 'interface_progress_prompt', value=value), reply_markup=cancel_keyboard(lang=lang))
    await InterfaceSettingsState.waiting_for_progress.set()

@dp.message_handler(state=InterfaceSettingsState.waiting_for_progress)
async def process_interface_progress(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    if text in ['да', 'yes', 'y', 'oui', 'ja', '是']:
        new_value = True
    elif text in ['нет', 'no', 'n', 'non', 'nein', '否']:
        new_value = False
    else:
        await message.answer(translate(get_lang(message), 'input_error'), reply_markup=interface_menu_keyboard(lang=get_lang(message), role=get_user_role(message)))
        await state.finish()
        return
    if settings_manager.set_setting('interface.show_progress', new_value):
        status = 'включён' if new_value else 'выключен'
        await message.answer(translate(get_lang(message), 'interface_progress_set', status=status), reply_markup=interface_menu_keyboard(lang=get_lang(message), role=get_user_role(message)))
    else:
        await message.answer(translate(get_lang(message), 'settings_error'), reply_markup=interface_menu_keyboard(lang=get_lang(message), role=get_user_role(message)))
    await state.finish()

@dp.message_handler(is_menu_button('interface_time_btn'))
async def handle_interface_time(message: Message):
    current = settings_manager.get_setting('interface.show_time', True)
    value = 'да' if current else 'нет'
    lang = get_lang(message)
    await message.answer(translate(lang, 'interface_time_prompt', value=value), reply_markup=cancel_keyboard(lang=lang))
    await InterfaceSettingsState.waiting_for_time.set()

@dp.message_handler(state=InterfaceSettingsState.waiting_for_time)
async def process_interface_time(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    lang = get_lang(message)
    if text in ['да', 'yes', 'y', 'oui', 'ja', '是']:
        new_value = True
    elif text in ['нет', 'no', 'n', 'non', 'nein', '否']:
        new_value = False
    else:
        await message.answer(translate(get_lang(message), 'input_error'), reply_markup=interface_menu_keyboard(lang=get_lang(message), role=get_user_role(message)))
        await state.finish()
        return
    if settings_manager.set_setting('interface.show_time', new_value):
        status = 'включён' if new_value else 'выключен'
        await message.answer(translate(get_lang(message), 'interface_time_set', status=status), reply_markup=interface_menu_keyboard(lang=get_lang(message), role=get_user_role(message)))
    else:
        await message.answer(translate(get_lang(message), 'settings_error'), reply_markup=interface_menu_keyboard(lang=get_lang(message), role=get_user_role(message)))
    await state.finish()

@dp.message_handler(is_menu_button('interface_compact_btn'))
async def handle_interface_compact(message: Message):
    current = settings_manager.get_setting('interface.compact_mode', False)
    value = 'да' if current else 'нет'
    lang = get_lang(message)
    await message.answer(translate(lang, 'interface_compact_prompt', value=value), reply_markup=cancel_keyboard(lang=lang))
    await InterfaceSettingsState.waiting_for_compact.set()

@dp.message_handler(state=InterfaceSettingsState.waiting_for_compact)
async def process_interface_compact(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    lang = get_lang(message)
    if text in ['да', 'yes', 'y', 'oui', 'ja', '是']:
        new_value = True
    elif text in ['нет', 'no', 'n', 'non', 'nein', '否']:
        new_value = False
    else:
        await message.answer(translate(get_lang(message), 'input_error'), reply_markup=interface_menu_keyboard(lang=get_lang(message), role=get_user_role(message)))
        await state.finish()
        return
    if settings_manager.set_setting('interface.compact_mode', new_value):
        status = 'включён' if new_value else 'выключен'
        await message.answer(translate(get_lang(message), 'interface_compact_set', status=status), reply_markup=interface_menu_keyboard(lang=get_lang(message), role=get_user_role(message)))
    else:
        await message.answer(translate(get_lang(message), 'settings_error'), reply_markup=interface_menu_keyboard(lang=get_lang(message), role=get_user_role(message)))
    await state.finish()

@dp.message_handler(is_menu_button('security_users_btn'))
async def handle_security_users(message: Message):
    if not check_admin(message):
        await send_admin_only(message)
        return
    current = settings_manager.get_setting('security.operators', [])
    current_str = ', '.join(map(str, current)) if current else 'не задано'
    lang = get_lang(message)
    await message.answer(translate(lang, 'security_users_prompt', value=current_str), reply_markup=cancel_keyboard(lang=lang))
    await SecuritySettingsState.waiting_for_users.set()

@dp.message_handler(state=SecuritySettingsState.waiting_for_users)
async def process_security_users(message: Message, state: FSMContext):
    if not check_admin(message):
        await send_admin_only(message)
        await state.finish()
        return
    text = message.text.replace('\n', ',').replace(';', ',')
    users = [u.strip() for u in text.split(',') if u.strip().isdigit()]
    lang = get_lang(message)
    if not users:
        await message.answer(translate(lang, 'security_users_error'), reply_markup=security_menu_keyboard(lang=lang))
        await state.finish()
        return
    users = [int(u) for u in users]
    if settings_manager.set_setting('security.operators', users):
        await message.answer(translate(lang, 'security_users_set', value=', '.join(map(str, users))), reply_markup=security_menu_keyboard(lang=lang))
    else:
        await message.answer(translate(lang, 'security_users_save_error'), reply_markup=security_menu_keyboard(lang=lang))
    await state.finish()

@dp.message_handler(is_menu_button('security_log_level_btn'))
async def handle_security_log_level(message: Message):
    current = settings_manager.get_setting('security.log_level', 'INFO')
    lang = get_lang(message)
    await message.answer(translate(lang, 'security_log_level_prompt', value=current), reply_markup=cancel_keyboard(lang=lang))
    await SecuritySettingsState.waiting_for_log_level.set()

@dp.message_handler(state=SecuritySettingsState.waiting_for_log_level)
async def process_security_log_level(message: Message, state: FSMContext):
    level = message.text.strip().upper()
    lang = get_lang(message)
    if level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
        await message.answer(translate(lang, 'security_log_level_error'), reply_markup=security_menu_keyboard(lang=lang))
        await state.finish()
        return
    if settings_manager.set_setting('security.log_level', level):
        await message.answer(translate(lang, 'security_log_level_set', value=level), reply_markup=security_menu_keyboard(lang=lang))
    else:
        await message.answer(translate(lang, 'security_log_level_save_error'), reply_markup=security_menu_keyboard(lang=lang))
    await state.finish()

@dp.message_handler(is_menu_button('backup_auto_btn'))
async def handle_backup_auto(message: Message):
    current = settings_manager.get_setting('backup.auto', False)
    value = 'да' if current else 'нет'
    lang = get_lang(message)
    await message.answer(translate(lang, 'backup_auto_prompt', value=value), reply_markup=cancel_keyboard(lang=lang))
    await BackupSettingsState.waiting_for_auto.set()

@dp.message_handler(is_menu_button('backup_interval_btn'))
async def handle_backup_interval(message: Message):
    current = settings_manager.get_setting('backup.interval', 24)
    lang = get_lang(message)
    await message.answer(translate(lang, 'backup_interval_prompt', value=current), reply_markup=cancel_keyboard(lang=lang))
    await BackupSettingsState.waiting_for_interval.set()

@dp.message_handler(is_menu_button('backup_max_count_btn'))
async def handle_backup_max_count(message: Message):
    current = settings_manager.get_setting('backup.max_count', 10)
    lang = get_lang(message)
    await message.answer(translate(lang, 'backup_max_count_prompt', value=current), reply_markup=cancel_keyboard(lang=lang))
    await BackupSettingsState.waiting_for_max_count.set()

@dp.message_handler(is_menu_button('import_settings_btn'))
async def handle_import_settings_btn(message: Message):
    lang = get_lang(message)
    await message.answer(translate(lang, 'backup_import_prompt'), reply_markup=cancel_keyboard(lang=lang))
    await BackupSettingsState.waiting_for_import.set()

@dp.message_handler(is_menu_button('export_settings_btn'))
async def handle_export_settings_btn(message: Message):
    lang = get_lang(message)
    json_str = settings_manager.export_settings()
    await message.answer_document(('settings_export.json', json_str.encode('utf-8')), caption=translate(lang, 'settings_exported'), reply_markup=export_menu_keyboard(lang=lang))

@dp.message_handler(is_menu_button('export_stats_btn'))
async def handle_export_stats_btn(message: Message):
    lang = get_lang(message)
    await message.answer(translate(lang, 'export_stats_msg'), reply_markup=export_menu_keyboard(lang=lang))

@dp.message_handler(is_menu_button('export_logs_btn'))
async def handle_export_logs_btn(message: Message):
    lang = get_lang(message)
    await message.answer(translate(lang, 'export_logs_msg'), reply_markup=export_menu_keyboard(lang=lang))

@dp.message_handler(is_menu_button('settings_summary'))
async def handle_settings_summary(message: Message):
    router_status = await background_monitor.get_current_status()
    online_routers = sum(1 for s in router_status.values() if s == 'online')
    offline_routers = sum(1 for s in router_status.values() if s != 'online')
    summary = settings_manager.get_settings_summary(
        background_monitor=background_monitor,
        notification_manager=notification_manager,
        scan_manager=scan_manager,
        online_routers=online_routers,
        offline_routers=offline_routers
    )
    lang = get_lang(message)
    role = get_user_role(message)
    await message.answer(summary, parse_mode='Markdown', reply_markup=settings_main_menu_keyboard(lang=lang, role=role))

@dp.message_handler(is_menu_button('settings_reset'))
async def handle_settings_reset(message: Message):
    ok = settings_manager.reset_to_defaults()
    if ok:
        await message.answer(translate(get_lang(message), 'settings_reset'), reply_markup=settings_main_menu_keyboard(lang=get_lang(message), role=get_user_role(message)))
    else:
        await message.answer(translate(get_lang(message), 'settings_reset_error'), reply_markup=settings_main_menu_keyboard(lang=get_lang(message), role=get_user_role(message)))

@dp.message_handler(is_menu_button('cancel'), state='*')
async def cancel_any_state(message: Message, state: FSMContext):
    await state.finish()
    await message.answer('Действие отменено.', reply_markup=settings_main_menu_keyboard(lang=get_lang(message), role=get_user_role(message)))

@dp.message_handler(is_menu_button('back_to_main_btn'), state='*')
async def handle_back_to_main_any(message: Message, state: FSMContext):
    lang = get_lang(message)
    role = get_user_role(message)
    await message.answer(translate(lang, 'main_menu'), reply_markup=main_menu_keyboard(lang=lang, role=role))
    # Не завершаем FSM, если оно есть

@dp.message_handler(is_menu_button('help_btn'))
async def handle_help_btn(message: Message):
    lang = get_lang(message)
    await message.answer(translate(lang, 'help_menu_msg'), reply_markup=help_menu_keyboard(lang=lang))

@dp.message_handler(is_menu_button('help_bot_btn'))
async def handle_help_bot_btn(message: Message):
    lang = get_lang(message)
    await message.answer(translate(lang, 'help_bot_text'), reply_markup=help_menu_keyboard(lang=lang))

@dp.message_handler(lambda m: m.text.lower() == 'файл', state=ScanDevicesState.waiting_for_file_request)
async def send_devices_file(message: Message, state: FSMContext):
    if not message.reply_to_message:
        await message.answer("Пожалуйста, используйте reply на сообщение с результатами.")
        await state.finish()
        return
    msg_id = message.reply_to_message.message_id
    file_path = scan_manager.get_result_file(msg_id, ext='csv')
    lang = get_lang(message)
    if file_path and os.path.exists(file_path):
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(text=translate(lang, 'get_ip_list_btn'), callback_data=f'get_ips_file:{file_path}'))
        with open(file_path, 'rb') as f:
            await message.answer_document(f, caption=translate(lang, 'scan_file_sent'), reply_markup=kb)
    else:
        await message.answer(translate(lang, 'scan_file_not_found'))
    await state.finish()

@dp.message_handler(lambda m: m.text.lower() == 'файл', state=ScanMinersState.waiting_for_file_request)
async def send_miners_file(message: Message, state: FSMContext):
    if not message.reply_to_message:
        await message.answer("Пожалуйста, используйте reply на сообщение с результатами.")
        await state.finish()
        return
    msg_id = message.reply_to_message.message_id
    file_path = scan_manager.get_result_file(msg_id, ext='csv')
    lang = get_lang(message)
    if file_path and os.path.exists(file_path):
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(text=translate(lang, 'get_ip_list_btn'), callback_data=f'get_ips_file:{file_path}'))
        with open(file_path, 'rb') as f:
            await message.answer_document(f, caption=translate(lang, 'scan_file_sent'), reply_markup=kb)
    else:
        await message.answer(translate(lang, 'scan_file_not_found'))
    await state.finish()

@dp.message_handler(lambda m: m.text.lower() == 'файл', state=FastScanState.waiting_for_file_request)
async def send_fastscan_file(message: Message, state: FSMContext):
    if not message.reply_to_message:
        await message.answer("Пожалуйста, используйте reply на сообщение с результатами.")
        await state.finish()
        return
    msg_id = message.reply_to_message.message_id
    file_path = scan_manager.get_result_file(msg_id, ext='csv')
    lang = get_lang(message)
    if file_path and os.path.exists(file_path):
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(text=translate(lang, 'get_ip_list_btn'), callback_data=f'get_ips_file:{file_path}'))
        with open(file_path, 'rb') as f:
            await message.answer_document(f, caption=translate(lang, 'scan_file_sent'), reply_markup=kb)
    else:
        await message.answer(translate(lang, 'scan_file_not_found'))
    await state.finish()

@dp.message_handler(is_menu_button('snmp_router_menu_btn'))
async def handle_snmp_router_menu(message: Message):
    lang = get_lang(message)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'snmp_router_status_btn')))
    kb.row(KeyboardButton(translate(lang, 'snmp_router_settings_btn')))
    kb.row(KeyboardButton(translate(lang, 'snmp_router_community_btn')))
    kb.row(KeyboardButton(translate(lang, 'snmp_router_extended_btn')))
    kb.row(KeyboardButton(translate(lang, 'back_to_main_btn')))
    await message.answer(translate(lang, 'snmp_router_menu_msg'), reply_markup=kb)

@dp.message_handler(is_menu_button('snmp_router_status_btn'))
async def handle_snmp_router_status(message: Message):
    lang = get_lang(message)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'snmp_router_menu_btn')))
    snmp_settings = settings_manager.get_setting('snmp_routers', {})
    ips = snmp_settings.get('ips')
    community = snmp_settings.get('community', 'public')
    if not ips or not isinstance(ips, list) or not ips:
        ips = settings_manager.get_setting('routers.ips', [])
    if not ips:
        await message.answer('Список SNMP роутеров пуст.', reply_markup=kb)
        return
    text = '<b>Статус SNMP роутеров:</b>\n'
    tasks = [async_get_snmp_info_subprocess(ip, community) for ip in ips]
    results = await asyncio.gather(*tasks)
    for ip, info in zip(ips, results):
        text += f'\n<code>{ip}</code>:'
        text += f"\n  sysName: {info.get('sysName', '-') }"
        text += f"\n  sysDescr: {info.get('sysDescr', '-') }"
        text += f"\n  sysUpTime: {info.get('sysUpTime', '-') }"
    await message.answer(text, parse_mode='HTML', reply_markup=kb)

@dp.message_handler(is_menu_button('snmp_router_settings_btn'))
async def handle_snmp_router_settings(message: Message):
    lang = get_lang(message)
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'snmp_router_menu_btn')))
    await message.answer('Настройки SNMP роутеров: (заглушка)', reply_markup=kb)

@dp.message_handler(is_menu_button('snmp_router_community_btn'))
async def handle_snmp_router_community(message: Message):
    lang = get_lang(message)
    if not check_admin(message):
        await message.answer(translate(lang, 'admin_only'))
        return
    current = settings_manager.get_setting('snmp_routers.community', 'public')
    await message.answer(translate(lang, 'snmp_router_community_prompt', value=current))
    await SnmpRouterSettingsState.waiting_for_community.set()

@dp.message_handler(state=SnmpRouterSettingsState.waiting_for_community)
async def process_snmp_router_community(message: Message, state: FSMContext):
    lang = get_lang(message)
    if not check_admin(message):
        await message.answer(translate(lang, 'admin_only'))
        await state.finish()
        return
    value = message.text.strip()
    settings_manager.set_setting('snmp_routers.community', value)
    await message.answer(translate(lang, 'snmp_router_community_set', value=value))
    await state.finish()

@dp.message_handler(is_menu_button('snmp_router_extended_btn'))
async def handle_snmp_router_extended_btn(message: Message, state: FSMContext):
    lang = get_lang(message)
    snmp_settings = settings_manager.get_setting('snmp_routers', {})
    ips = snmp_settings.get('ips')
    if not ips or not isinstance(ips, list) or not ips:
        ips = settings_manager.get_setting('routers.ips', [])
    if not ips:
        await message.answer('Список SNMP роутеров пуст.')
        return
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for ip in ips:
        kb.row(KeyboardButton(ip))
    kb.row(KeyboardButton(translate(lang, 'snmp_router_menu_btn')))
    await message.answer(translate(lang, 'snmp_router_extended_select_prompt'), reply_markup=kb)
    await SnmpRouterExtendedState.waiting_for_router.set()
    await state.update_data(ips=ips)

@dp.message_handler(is_menu_button('snmp_router_menu_btn'), state=SnmpRouterExtendedState.waiting_for_router)
async def snmp_router_extended_back_to_menu(message: Message, state: FSMContext):
    await state.finish()
    await handle_snmp_router_menu(message)

@dp.message_handler(state=SnmpRouterExtendedState.waiting_for_router)
async def handle_snmp_router_extended_select(message: Message, state: FSMContext):
    lang = get_lang(message)
    data = await state.get_data()
    ips = data.get('ips', [])
    ip = message.text.strip()
    if ip not in ips:
        await message.answer('Выберите роутер из списка.')
        return
    snmp_settings = settings_manager.get_setting('snmp_routers', {})
    community = snmp_settings.get('community', 'public')
    await message.answer(translate(lang, 'snmp_router_extended_loading'))
    info = await async_get_snmp_full_info(ip, community)
    text = f'<b>Расширенный SNMP-запрос для {ip}:</b>'
    text += f"\n  sysName: {info.get('sysName', '-') }"
    text += f"\n  sysDescr: {info.get('sysDescr', '-') }"
    text += f"\n  sysUpTime: {info.get('sysUpTime', '-') }"
    text += f"\n  sysContact: {info.get('sysContact', '-') }"
    text += f"\n  sysLocation: {info.get('sysLocation', '-') }"
    text += f"\n  ifNumber: {info.get('ifNumber', '-') }"
    interfaces = info.get('interfaces', [])
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton(translate(lang, 'snmp_router_menu_btn')))
    if interfaces:
        text += f"\n  <b>Интерфейсы (первые 10):</b>"
        for idx, iface in enumerate(interfaces[:10], 1):
            text += f"\n    {idx}. {iface['descr']} | Статус: {iface['status']} | RX: {iface['in_octets']} | TX: {iface['out_octets']}"
        if len(interfaces) > 10:
            kb.row(KeyboardButton('...'))
    await message.answer(text, parse_mode='HTML', reply_markup=kb)

@dp.message_handler(lambda m: m.reply_to_message is not None)
async def resend_scan_result_file(message: Message):
    if getattr(message.reply_to_message, 'document', None):
        return
    result = scan_manager.get_results().get(message.reply_to_message.message_id)
    network = None
    scan_type = None
    lang = get_lang(message)
    if result:
        network = result.get('network')
        scan_type = scan_manager.get_scan_type_for_result(result)
        logging.info(f"[REPLY] Найден результат в памяти: network={network}, scan_type={scan_type}")
    else:
        text = message.reply_to_message.text or ''
        logging.info(f"[REPLY] Результат не найден в памяти. Пробую извлечь из текста: {text}")
        # Ищем строку с сетью
        net_match = re.search(r'Сканирование сети: ([\d\.]+/\d+)', text)
        if net_match:
            network = net_match.group(1)
        if not network:
            net_match = re.search(r'(\d+\.\d+\.\d+\.\d+/\d+)', text)
            if net_match:
                network = net_match.group(1)
        if 'Найдено майнеров' in text:
            scan_type = 'miners'
        elif 'Найдено устройств' in text:
            scan_type = 'scan'
        elif 'Быстрое сканирование' in text or 'fast scan' in text.lower():
            scan_type = 'fast_scan'
        logging.info(f"[REPLY] Извлечено из текста: network={network}, scan_type={scan_type}")
    file_path = None
    if network and scan_type:
        file_path = scan_manager.get_scan_result_file(scan_type, network, ext='csv')
        if not file_path:
            file_path = scan_manager.get_scan_result_file(scan_type, network, ext='json')
    # Резервный поиск, если не удалось найти файл
    if not file_path and scan_type == 'miners':
        import glob
        scan_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/scan_results'))
        files = glob.glob(os.path.join(scan_dir, 'miners_*.csv'))
        if files:
            file_path = max(files, key=os.path.getctime)
            await message.answer(translate(lang, 'scan_file_not_found_try_last'), reply_markup=main_menu_keyboard(lang=lang))
    if file_path and os.path.exists(file_path):
        await message.answer_document(open(file_path, 'rb'), caption=translate(lang, 'scan_file_sent'), reply_markup=main_menu_keyboard(lang=lang))
    else:
        await message.answer(translate(lang, 'scan_file_not_found'), reply_markup=main_menu_keyboard(lang=lang))

@dp.message_handler(lambda m: m.reply_to_message and hasattr(m.reply_to_message, 'document') and m.reply_to_message.document)
async def send_ip_list_from_scan_file(message: Message):
    await message.answer('DEBUG: обработчик файла вызван')
    file = message.reply_to_message.document
    file_name = file.file_name
    try:
        file_obj = await file.download()
        file_obj.seek(0)
        ips = set()
        if file_name.endswith('.csv'):
            import csv
            reader = csv.DictReader(file_obj.read().decode('utf-8').splitlines())
            for row in reader:
                ip = row.get('ip') or row.get('IP')
                if ip:
                    ips.add(ip.strip())
        elif file_name.endswith('.json'):
            import json
            data = json.load(file_obj)
            items = data.get('devices') or data.get('miners') or []
            for d in items:
                ip = d.get('ip') or d.get('IP')
                if ip:
                    ips.add(ip.strip())
        else:
            await message.answer('Формат файла не поддерживается.', reply_markup=main_menu_keyboard(lang=get_lang(message)))
            return
        if ips:
            await message.answer(','.join(sorted(ips)), reply_markup=main_menu_keyboard(lang=get_lang(message)))
        else:
            await message.answer('IP-адреса не найдены в файле.', reply_markup=main_menu_keyboard(lang=get_lang(message)))
    except Exception as e:
        await message.answer(f'Ошибка при обработке файла: {e}', reply_markup=main_menu_keyboard(lang=get_lang(message)))

@dp.message_handler(lambda m: m.reply_to_message is not None)
async def debug_reply(message: Message):
    info = []
    info.append(f"DEBUG: reply handler called")
    if hasattr(message.reply_to_message, 'document'):
        info.append(f"has document: {bool(message.reply_to_message.document)}")
        if message.reply_to_message.document:
            info.append(f"file_name: {message.reply_to_message.document.file_name}")
    else:
        info.append("no document attr")
    await message.answer(' | '.join(info))

@dp.message_handler(commands=['get_ips'])
async def get_ips_from_scan_file(message: Message):
    if message.reply_to_message and hasattr(message.reply_to_message, 'document') and message.reply_to_message.document:
        file = message.reply_to_message.document
        file_name = file.file_name
        try:
            file_obj = await file.download()
            file_obj.seek(0)
            ips = set()
            if file_name.endswith('.csv'):
                import csv
                reader = csv.DictReader(file_obj.read().decode('utf-8').splitlines())
                for row in reader:
                    ip = row.get('ip') or row.get('IP')
                    if ip:
                        ips.add(ip.strip())
            elif file_name.endswith('.json'):
                import json
                data = json.load(file_obj)
                items = data.get('devices') or data.get('miners') or []
                for d in items:
                    ip = d.get('ip') or d.get('IP')
                    if ip:
                        ips.add(ip.strip())
            else:
                await message.answer('Формат файла не поддерживается.', reply_markup=main_menu_keyboard(lang=get_lang(message)))
                return
            if ips:
                await message.answer(','.join(sorted(ips)), reply_markup=main_menu_keyboard(lang=get_lang(message)))
            else:
                await message.answer('IP-адреса не найдены в файле.', reply_markup=main_menu_keyboard(lang=get_lang(message)))
        except Exception as e:
            await message.answer(f'Ошибка при обработке файла: {e}', reply_markup=main_menu_keyboard(lang=get_lang(message)))
    else:
        await message.answer('Сделайте /get_ips в reply на файл с результатами сканирования.', reply_markup=main_menu_keyboard(lang=get_lang(message)))

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('get_ips:'))
async def handle_get_ips_callback(call: CallbackQuery):
    file_name = call.data.split(':', 1)[1]
    file_path = os.path.join('telegram_bot/data/scan_results', file_name)
    if not os.path.exists(file_path):
        await call.message.answer('Файл не найден.', reply_markup=main_menu_keyboard(lang=get_lang(call.message)))
        return
    ips = set()
    try:
        if file_name.endswith('.csv'):
            import csv
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ip = row.get('ip') or row.get('IP')
                    if ip:
                        ips.add(ip.strip())
        elif file_name.endswith('.json'):
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                items = data.get('devices') or data.get('miners') or []
                for d in items:
                    ip = d.get('ip') or d.get('IP')
                    if ip:
                        ips.add(ip.strip())
        else:
            await call.message.answer('Формат файла не поддерживается.', reply_markup=main_menu_keyboard(lang=get_lang(call.message)))
            return
        if ips:
            await call.message.answer(','.join(sorted(ips)), reply_markup=main_menu_keyboard(lang=get_lang(call.message)))
        else:
            await call.message.answer('IP-адреса не найдены в файле.', reply_markup=main_menu_keyboard(lang=get_lang(call.message)))
    except Exception as e:
        await call.message.answer(f'Ошибка при обработке файла: {e}', reply_markup=main_menu_keyboard(lang=get_lang(call.message)))
    await call.answer()

@dp.message_handler(commands=['scanfiles'])
async def handle_scanfiles(message: Message):
    scan_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/scan_results'))
    try:
        files = os.listdir(scan_dir)
        if not files:
            await message.answer(translate(get_lang(message), 'no_scan_files'))
            return
        kb = InlineKeyboardMarkup()
        for fname in files:
            kb.add(InlineKeyboardButton(fname, callback_data=f'scanips:{fname}'))
        await message.answer(translate(get_lang(message), 'scan_files_list'), reply_markup=kb)
    except Exception as e:
        await message.answer(translate(get_lang(message), 'scan_files_error', e=e))

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('scanips:'))
async def handle_scanips_callback(call: CallbackQuery):
    filename = call.data.split(':', 1)[1]
    scan_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/scan_results'))
    file_path = os.path.join(scan_dir, filename)
    if not os.path.exists(file_path):
        await call.message.answer(translate(get_lang(call.message), 'scan_file_not_found'))
        await call.answer()
        return
    ips = set()
    try:
        if filename.endswith('.csv'):
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ip = row.get('ip') or row.get('IP')
                    if ip:
                        ips.add(ip.strip())
        elif filename.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                items = data.get('devices') or data.get('miners') or []
                for d in items:
                    ip = d.get('ip') or d.get('IP')
                    if ip:
                        ips.add(ip.strip())
        else:
            await call.message.answer(translate(get_lang(call.message), 'scan_file_format_error'))
            await call.answer()
            return
        if ips:
            await call.message.answer(','.join(sorted(ips)))
        else:
            await call.message.answer(translate(get_lang(call.message), 'scan_file_no_ips'))
    except Exception as e:
        await call.message.answer(translate(get_lang(call.message), 'scan_file_read_error', e=e))
    await call.answer()

@dp.message_handler(commands=['role'])
async def handle_role_command(message: Message):
    lang = get_lang(message)
    role = get_user_role(message)
    if role == 'admin':
        text = translate(lang, 'role_admin')
    elif role == 'operator':
        text = translate(lang, 'role_operator')
    else:
        text = translate(lang, 'role_none')
    await message.answer(text, reply_markup=main_menu_keyboard(lang=lang, role=role))

@dp.message_handler(is_menu_button('asic_status_main_menu_btn'))
async def handle_asic_status_main_menu(message: Message):
    lang = get_lang(message)
    role = get_user_role(message)
    asic_ips = settings_manager.get_setting('miners.ips', [])
    if not asic_ips:
        await message.answer(translate(lang, 'asic_list_empty'), reply_markup=main_menu_keyboard(lang=lang, role=role))
        return
    await message.answer(translate(lang, 'checking_asics'), reply_markup=main_menu_keyboard(lang=lang, role=role))
    results = []
    for ip in asic_ips:
        try:
            status = await get_asic_status(ip)
            if status:
                hashrate = status.get('hashrate') or status.get('GHS 5s') or status.get('SUMMARY', [{}])[0].get('GHS 5s') or '-'
                uptime = status.get('uptime') or status.get('SUMMARY', [{}])[0].get('Elapsed') or '-'
                uptime_str = format_uptime(uptime) if uptime not in (None, '-', '') else '-'
                online = status.get('status', 'offline') == 'online' or status.get('is_hashing')
                text = f"{ip}: {'🟢' if online else '🔴'}, hashrate: {hashrate} GH/s, uptime: {uptime_str}"
            else:
                text = f"{ip}: нет ответа"
        except Exception as e:
            text = f"{ip}: ошибка — {e}"
        results.append(text)
    await message.answer('\n'.join(results), reply_markup=main_menu_keyboard(lang=lang, role=role))

@dp.message_handler(is_menu_button('asic_ips_btn'))
async def handle_asic_ips_btn(message: Message, state: FSMContext):
    if get_user_role(message) != 'admin':
        await send_access_denied(message)
        return
    lang = get_lang(message)
    asic_ips = settings_manager.get_setting('miners.ips', [])
    value = ', '.join(asic_ips) if asic_ips else '-'
    await message.answer(
        translate(lang, 'asic_ips_prompt', value=value),
        reply_markup=asic_ips_cancel_keyboard(lang=lang)
    )
    await AsicSettingsState.waiting_for_ips.set()

@dp.message_handler(lambda m: m.text == translate(get_lang(m), 'cancel_btn'), state=AsicSettingsState.waiting_for_ips)
async def cancel_asic_ips_input(message: Message, state: FSMContext):
    lang = get_lang(message)
    role = get_user_role(message)
    await state.finish()
    await message.answer(translate(lang, 'settings_menu_msg'), reply_markup=settings_main_menu_keyboard(lang=lang, role=role))

@dp.message_handler(state=AsicSettingsState.waiting_for_ips)
async def process_asic_ips_input(message: Message, state: FSMContext):
    if get_user_role(message) != 'admin':
        await send_access_denied(message)
        await state.finish()
        return
    lang = get_lang(message)
    text = message.text.strip()
    # Разделяем по запятой, убираем пробелы
    ip_list = [ip.strip() for ip in text.split(',') if ip.strip()]
    # Проверяем корректность IP
    import ipaddress
    try:
        for ip in ip_list:
            ipaddress.IPv4Address(ip)
    except Exception:
        await message.answer(translate(lang, 'asic_ips_error'), reply_markup=settings_main_menu_keyboard(lang=lang, role=get_user_role(message)))
        await state.finish()
        return
    settings_manager.set_setting('miners.ips', ip_list)
    await message.answer(translate(lang, 'asic_ips_set', value=', '.join(ip_list)), reply_markup=settings_main_menu_keyboard(lang=lang, role=get_user_role(message)))
    await state.finish()

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('get_ips_file:'))
async def handle_get_ips_file_callback(call: CallbackQuery):
    lang = get_lang(call.message)
    file_path = call.data.split(':', 1)[1]
    if not os.path.exists(file_path):
        await call.message.answer(translate(lang, 'file_not_found'))
        await call.answer()
        return
    ips = set()
    try:
        if file_path.endswith('.csv'):
            import csv
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ip = row.get('ip') or row.get('IP')
                    if ip:
                        ips.add(ip.strip())
        elif file_path.endswith('.json'):
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                items = data.get('devices') or data.get('miners') or []
                for d in items:
                    ip = d.get('ip') or d.get('IP')
                    if ip:
                        ips.add(ip.strip())
        else:
            await call.message.answer(translate(lang, 'file_format_error'))
            await call.answer()
            return
        if ips:
            await call.message.answer(','.join(sorted(ips)))
        else:
            await call.message.answer(translate(lang, 'no_ips_found'))
    except Exception as e:
        await call.message.answer(translate(lang, 'file_processing_error', e=e))
    await call.answer()

def format_uptime(uptime):
    try:
        uptime = int(float(uptime))
        days = uptime // 86400
        hours = (uptime % 86400) // 3600
        minutes = (uptime % 3600) // 60
        parts = []
        if days > 0:
            parts.append(f"{days}д")
        if hours > 0 or days > 0:
            parts.append(f"{hours}ч")
        parts.append(f"{minutes}м")
        return ' '.join(parts)
    except Exception:
        return str(uptime)

@dp.message_handler(is_menu_button('scan_files_main_menu_btn'))
async def handle_scan_files_main_menu(message: Message):
    await handle_scanfiles(message)

if __name__ == '__main__':
    executor.start_polling(
        dp, 
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    ) 