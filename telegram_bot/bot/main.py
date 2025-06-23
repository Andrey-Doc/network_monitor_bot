import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import Message, ContentType, ReplyKeyboardMarkup, KeyboardButton
from .keyboards import (
    main_menu_keyboard, settings_menu_keyboard, monitoring_menu_keyboard,
    scan_menu_keyboard, notification_menu_keyboard, router_menu_keyboard,
    interface_menu_keyboard, security_menu_keyboard, backup_menu_keyboard,
    export_menu_keyboard, help_menu_keyboard, cancel_keyboard,
    scan_main_menu_keyboard, settings_main_menu_keyboard
)
from ..utils.router_monitor import check_routers_status
from ..utils.miner_scan import scan_network_for_miners, scan_miners_from_list
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

logging.basicConfig(level=logging.INFO)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))
settings_manager = SettingsManager(os.path.join(UPLOAD_DIR, 'settings.json'), config_py="bot/config.py")

# Получаем основные параметры из settings_manager
TELEGRAM_BOT_TOKEN = settings_manager.get_setting('TELEGRAM_BOT_TOKEN')
CHAT_ID = settings_manager.get_setting('CHAT_ID')
ROUTER_IPS = settings_manager.get_setting('ROUTER_IPS')
ROUTER_PORTS = settings_manager.get_setting('ROUTER_PORTS')
SCAN_RESULTS_TTL = settings_manager.get_setting('SCAN_RESULTS_TTL', 3600)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Инициализация ScanManager
scan_manager = ScanManager(ttl=settings_manager.get_setting('scanning.results_ttl', 3600))

# Инициализация новых модулей
background_monitor = BackgroundMonitor(bot, CHAT_ID)
notification_manager = NotificationManager(bot)
statistics_manager = StatisticsManager(UPLOAD_DIR)
help_system = HelpSystem()

# SCAN_RESULTS_TTL: сначала из настроек, потом из config.py
SCAN_RESULTS_TTL = settings_manager.get_setting('scanning.results_ttl') or SCAN_RESULTS_TTL
# DEFAULT_TIMEOUT: сначала из настроек, потом дефолт
DEFAULT_TIMEOUT = settings_manager.get_setting('scanning.default_timeout') or 5

def get_lang():
    return settings_manager.get_setting('interface.language', 'ru')

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
    waiting_for_admin_only = State()

class BackupSettingsState(StatesGroup):
    waiting_for_interval = State()
    waiting_for_max_count = State()
    waiting_for_import = State()
    waiting_for_auto = State()

# --- Universal menu button filter ---
def is_menu_button(key):
    def inner(m):
        lang = settings_manager.get_setting('interface.language', 'ru')
        return m.text == translate(lang, key)
    return inner

@dp.message_handler(commands=['start', 'menu'])
async def send_welcome(message: Message):
    statistics_manager.record_command('start')
    print(f"[INFO] Ваш chat_id: {message.chat.id}")
    logging.info(f"[INFO] Ваш chat_id: {message.chat.id}")
    await message.answer(
        translate(get_lang(), 'welcome'),
        reply_markup=main_menu_keyboard(lang=get_lang())
    )

@dp.message_handler(is_menu_button('status_btn'))
async def handle_status_btn(message: Message):
    await handle_status(message)

@dp.message_handler(is_menu_button('router_status_btn'))
async def handle_router_status_btn(message: Message):
    await handle_router_status_menu(message)

@dp.message_handler(is_menu_button('scan_main_menu_btn'))
async def handle_scan_main_menu(message: Message):
    await message.answer(translate(get_lang(), 'scan_menu_msg'), reply_markup=scan_main_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('settings_main_menu_btn'))
async def handle_settings_main_menu(message: Message):
    await message.answer(translate(get_lang(), 'settings_menu_msg'), reply_markup=settings_main_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('scan_network_btn'))
async def handle_scan_network_btn(message: Message):
    await handle_scan_network(message)

@dp.message_handler(is_menu_button('scan_miners_btn'))
async def handle_scan_miners_btn(message: Message):
    await handle_scan_miners(message)

@dp.message_handler(is_menu_button('fast_scan_btn'))
async def handle_fast_scan_btn(message: Message):
    await handle_fast_scan(message)

@dp.message_handler(is_menu_button('upload_file_btn'))
async def handle_upload_file_btn(message: Message):
    await handle_upload_file(message)

@dp.message_handler(is_menu_button('settings_menu_btn'))
async def handle_settings_menu_btn(message: Message):
    await message.answer(translate(get_lang(), 'settings_menu_msg'), reply_markup=settings_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('backup_menu_btn'))
async def handle_backup_menu_btn(message: Message):
    await message.answer(translate(get_lang(), 'backup_menu_msg'), reply_markup=backup_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('export_menu_btn'))
async def handle_export_menu_btn(message: Message):
    await message.answer(translate(get_lang(), 'export_menu_msg'), reply_markup=export_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('notification_menu_btn'))
async def handle_notification_menu(message: Message):
    await message.answer(translate(get_lang(), 'notification_menu_msg'), reply_markup=notification_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('router_menu_btn'))
async def handle_router_menu(message: Message):
    await message.answer(translate(get_lang(), 'router_menu_msg'), reply_markup=router_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('interface_menu_btn'))
async def handle_interface_menu(message: Message):
    await message.answer(translate(get_lang(), 'interface_menu_msg'), reply_markup=interface_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('security_menu_btn'))
async def handle_security_menu(message: Message):
    await message.answer(translate(get_lang(), 'security_menu_msg'), reply_markup=security_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('help_menu_btn'))
async def handle_help_menu(message: Message):
    await message.answer(translate(get_lang(), 'help_menu_msg'), reply_markup=help_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('back_to_main_btn'))
async def handle_back_to_main(message: Message):
    await message.answer(translate(get_lang(), 'main_menu'), reply_markup=main_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('back_to_settings_btn'))
async def handle_back_to_settings(message: Message):
    await message.answer(translate(get_lang(), 'settings_menu_msg'), reply_markup=settings_menu_keyboard(lang=get_lang()))

@dp.message_handler(commands=['help'])
async def handle_help_command(message: Message):
    """Команда для получения справки"""
    statistics_manager.record_command('help')
    help_text = help_system.get_main_help()
    await message.answer(
        help_text,
        parse_mode='Markdown',
        reply_markup=help_menu_keyboard(lang=get_lang())
    )

@dp.message_handler(commands=['status'])
async def handle_status(message: Message):
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
    """Команда для получения статистики"""
    report = statistics_manager.generate_report()
    await message.answer(report, parse_mode='Markdown')

@dp.message_handler(commands=['monitor_start'])
async def handle_monitor_start(message: Message):
    """Команда для запуска мониторинга"""
    await background_monitor.start_monitoring()
    await notification_manager.send_notification(
        level=NotificationLevel.SUCCESS,
        notification_type=NotificationType.SYSTEM_ALERT,
        title="Мониторинг запущен",
        message="Фоновый мониторинг роутеров успешно запущен"
    )
    await message.answer(translate(get_lang(), 'monitor_start_success'))

@dp.message_handler(commands=['monitor_stop'])
async def handle_monitor_stop(message: Message):
    """Команда для остановки мониторинга"""
    await background_monitor.stop_monitoring()
    await notification_manager.send_notification(
        level=NotificationLevel.INFO,
        notification_type=NotificationType.SYSTEM_ALERT,
        title="Мониторинг остановлен",
        message="Фоновый мониторинг роутеров остановлен"
    )
    await message.answer(translate(get_lang(), 'monitor_stop_success'))

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
            await message.answer(translate(get_lang(), 'timeout_error'))
            return
        if settings_manager.set_setting('scanning.default_timeout', timeout):
            await message.answer(translate(get_lang(), 'timeout_set', timeout=timeout))
        else:
            await message.answer(translate(get_lang(), 'timeout_save_error'))
    except Exception:
        await message.answer(translate(get_lang(), 'timeout_input_error'))
    await state.finish()

@dp.message_handler(lambda m: m.text == 'Статус роутеров')
async def handle_router_status(message: Message):
    statistics_manager.record_command('status_routers')
    await message.answer(translate(get_lang(), 'checking_routers'))
    results = await check_routers_status(ROUTER_IPS, ROUTER_PORTS)
    online_count = sum(1 for r in results if r['status'] == 'online')
    statistics_manager.record_router_check(online_count, len(ROUTER_IPS))
    text = "🌐 *Статус роутеров:*\n\n"
    for r in results:
        emoji = "🟢" if r['status'] == 'online' else "🔴"
        text += f"{emoji} *{r['ip']}*: {r['status']}\n"
        if r['open_ports']:
            text += f"   📡 Порт(ы): {', '.join(map(str, r['open_ports']))}\n"
        text += "\n"
    await message.answer(text, parse_mode='Markdown', reply_markup=main_menu_keyboard(lang=get_lang()))

@dp.message_handler(lambda m: m.text == 'Сканировать сеть')
async def handle_scan_network(message: Message):
    statistics_manager.record_command('scan_network')
    await message.answer(translate(get_lang(), 'scan_network_prompt'), reply_markup=scan_menu_keyboard(lang=get_lang()))
    await ScanDevicesState.waiting_for_network.set()

@dp.message_handler(state=ScanDevicesState.waiting_for_network)
async def process_devices_network_input(message: Message, state: FSMContext):
    cleanup_old_results()
    scan_manager.start_scan()
    network = message.text.strip()
    start_time = time.time()
    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except Exception as e:
        await message.answer(translate(get_lang(), 'network_format_error'), reply_markup=main_menu_keyboard(lang=get_lang()))
        scan_manager.finish_scan()
        await state.finish()
        return
    progress_msg = await message.answer(translate(get_lang(), 'scanning_network', network=network))
    async def on_progress(done, total):
        percent = int(done / total * 100)
        bar = '█' * (percent // 10) + '-' * (10 - percent // 10)
        await bot.edit_message_text(
            translate(get_lang(), 'scanning_progress', bar=bar, percent=percent, done=done, total=total),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
    try:
        devices = await scan_network_devices(network, on_progress=on_progress)
        duration = time.time() - start_time
        await bot.edit_message_text(
            translate(get_lang(), 'scan_completed', count=len(devices)),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        statistics_manager.record_scan('network', len(devices), net.num_addresses, duration)
        await notification_manager.scan_completed('сети', len(devices), duration)
        if not devices:
            await message.answer(translate(get_lang(), 'no_devices_found'), reply_markup=main_menu_keyboard(lang=get_lang()))
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
        result_msg = await message.answer(text, reply_markup=main_menu_keyboard(lang=get_lang()))
        scan_manager.add_result(result_msg.message_id, {
            'devices': devices,
            'type': 'devices',
            'timestamp': time.time()
        })
        await state.update_data(devices=devices)
        await ScanDevicesState.waiting_for_file_request.set()
    except Exception as e:
        await bot.edit_message_text(
            translate(get_lang(), 'scan_error', e=e),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        scan_manager.finish_scan()
        await state.finish()

@dp.message_handler(lambda m: m.text == 'Загрузить файл для сканирования')
async def handle_upload_file(message: Message):
    statistics_manager.record_command('upload_file')
    await message.answer(translate(get_lang(), 'upload_file_prompt'), reply_markup=main_menu_keyboard(lang=get_lang()))

@dp.message_handler(content_types=ContentType.DOCUMENT)
async def process_csv_file(message: Message):
    file = message.document
    if not file.file_name.lower().endswith('.csv'):
        await message.answer(translate(get_lang(), 'csv_format_error'), reply_markup=main_menu_keyboard(lang=get_lang()))
        return
    file_path = os.path.join(UPLOAD_DIR, file.file_name)
    await message.document.download(destination_file=file_path)
    try:
        df = pd.read_csv(file_path)
        if 'ip' not in df.columns:
            await message.answer(translate(get_lang(), 'ip_column_error'), reply_markup=main_menu_keyboard(lang=get_lang()))
            return
        ip_list = df['ip'].dropna().astype(str).tolist()
        await message.answer(
            translate(get_lang(), 'scanning_ips', count=len(ip_list)),
            reply_markup=main_menu_keyboard(lang=get_lang())
        )
        start_time = time.time()
        miners = await scan_miners_from_list(ip_list)
        duration = time.time() - start_time
        statistics_manager.record_scan('file_upload', len(miners), len(ip_list), duration)
        if not miners:
            await message.answer(translate(get_lang(), 'no_miners_found'), reply_markup=main_menu_keyboard(lang=get_lang()))
        else:
            text = "Результаты сканирования:\n"
            for m in miners:
                text += f"{m['ip']}: status={m['status']}, hashrate={m['hashrate']}, uptime={m['uptime']}\n"
            await message.answer(text, reply_markup=main_menu_keyboard(lang=get_lang()))
    except Exception as e:
        statistics_manager.record_error('file_processing', str(e))
        await message.answer(translate(get_lang(), 'file_processing_error', e=e), reply_markup=main_menu_keyboard(lang=get_lang()))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@dp.message_handler(lambda m: m.text == 'Сканировать майнеры')
async def handle_scan_miners(message: Message):
    statistics_manager.record_command('scan_miners')
    await message.answer(translate(get_lang(), 'scan_miners_prompt'), reply_markup=scan_menu_keyboard(lang=get_lang()))
    await ScanMinersState.waiting_for_network.set()

@dp.message_handler(state=ScanMinersState.waiting_for_network)
async def process_miners_network_input(message: Message, state: FSMContext):
    cleanup_old_results()
    scan_manager.start_scan()
    network = message.text.strip()
    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except Exception:
        await message.answer(translate(get_lang(), 'network_format_error'), reply_markup=main_menu_keyboard(lang=get_lang()))
        scan_manager.finish_scan()
        await state.finish()
        return
    progress_msg = await message.answer(translate(get_lang(), 'scanning_miners', network=network))
    async def on_progress(done, total):
        percent = int(done / total * 100)
        bar = '█' * (percent // 10) + '-' * (10 - percent // 10)
        await bot.edit_message_text(
            translate(get_lang(), 'scanning_progress', bar=bar, percent=percent, done=done, total=total),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
    try:
        miners = await scan_network_for_miners(network, on_progress=on_progress)
        await bot.edit_message_text(
            translate(get_lang(), 'scan_completed', count=len(miners)),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        if not miners:
            await message.answer(translate(get_lang(), 'no_miners_found'), reply_markup=main_menu_keyboard(lang=get_lang()))
            scan_manager.finish_scan()
            await state.finish()
            return
        text = "Найдено майнеров: {}\n".format(len(miners))
        for m in miners:
            text += f"{m['ip']}: miner (hashrate: {m.get('hashrate')}, uptime: {m.get('uptime')})\n"
        text += "\nЕсли хотите получить файл с результатами, напишите 'файл' в ответ или reply на это сообщение."
        result_msg = await message.answer(text, reply_markup=main_menu_keyboard(lang=get_lang()))
        scan_manager.add_result(result_msg.message_id, {
            'miners': miners,
            'type': 'miners',
            'timestamp': time.time()
        })
        await state.update_data(miners=miners)
        await ScanMinersState.waiting_for_file_request.set()
    except Exception as e:
        await bot.edit_message_text(
            translate(get_lang(), 'scan_error', e=e),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        scan_manager.finish_scan()
        await state.finish()

@dp.message_handler(lambda m: m.text == 'Быстрое сканирование сети')
async def handle_fast_scan(message: Message):
    await message.answer(translate(get_lang(), 'fast_scan_prompt'), reply_markup=scan_menu_keyboard(lang=get_lang()))
    await FastScanState.waiting_for_network.set()

@dp.message_handler(state=FastScanState.waiting_for_network)
async def process_fast_scan_network_input(message: Message, state: FSMContext):
    cleanup_old_results()
    scan_manager.start_scan()
    network = message.text.strip()
    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except Exception:
        await message.answer(translate(get_lang(), 'network_format_error'), reply_markup=main_menu_keyboard(lang=get_lang()))
        scan_manager.finish_scan()
        await state.finish()
        return
    progress_msg = await message.answer(translate(get_lang(), 'fast_scanning', network=network))
    async def on_progress(done, total):
        percent = int(done / total * 100)
        bar = '█' * (percent // 10) + '-' * (10 - percent // 10)
        await bot.edit_message_text(
            translate(get_lang(), 'fast_scanning_progress', bar=bar, percent=percent, done=done, total=total),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
    try:
        devices = await fast_scan_network(network, on_progress=on_progress)
        await bot.edit_message_text(
            translate(get_lang(), 'fast_scan_completed', count=len(devices)),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        if not devices:
            await message.answer(translate(get_lang(), 'no_devices_found'), reply_markup=main_menu_keyboard(lang=get_lang()))
            scan_manager.finish_scan()
            await state.finish()
            return
        text = f"Найдено устройств: {len(devices)}\n"
        for d in devices:
            if d.get('type') == 'miner':
                text += f"{d['ip']}: miner (hashrate: {d.get('hashrate')}, uptime: {d.get('uptime')})\n"
            else:
                text += f"{d['ip']}: {d.get('type', 'unknown')} (открытые порты: {', '.join(map(str, d['open_ports']))})\n"
        text += "\nЕсли хотите получить файл с результатами, напишите 'файл' в ответ или reply на это сообщение."
        result_msg = await message.answer(text, reply_markup=main_menu_keyboard(lang=get_lang()))
        scan_manager.add_result(result_msg.message_id, {
            'devices': devices,
            'type': 'fast_scan',
            'timestamp': time.time()
        })
        await state.update_data(devices=devices)
        await FastScanState.waiting_for_file_request.set()
    except Exception as e:
        await bot.edit_message_text(
            translate(get_lang(), 'fast_scan_error', e=e),
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        scan_manager.finish_scan()
        await state.finish()

@dp.message_handler(lambda m: m.text == 'Статистика')
async def handle_statistics(message: Message):
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
    await message.answer(report, parse_mode='Markdown', reply_markup=main_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('monitoring_interval'))
async def handle_monitoring_interval(message: Message):
    current = settings_manager.get_setting('monitoring.interval', 300)
    await message.answer(translate(get_lang(), 'monitoring_interval_prompt', value=current), reply_markup=cancel_keyboard(lang=get_lang()))
    await MonitoringState.waiting_for_interval.set()

@dp.message_handler(state=MonitoringState.waiting_for_interval)
async def process_monitoring_interval(message: Message, state: FSMContext):
    try:
        interval = int(message.text.strip())
        if interval < 10 or interval > 86400:
            await message.answer(translate(get_lang(), 'monitoring_interval_error'), reply_markup=monitoring_menu_keyboard(lang=get_lang()))
            return
        if settings_manager.set_setting('monitoring.interval', interval):
            await message.answer(translate(get_lang(), 'monitoring_interval_set', value=interval), reply_markup=monitoring_menu_keyboard(lang=get_lang()))
        else:
            await message.answer(translate(get_lang(), 'monitoring_interval_save_error'), reply_markup=monitoring_menu_keyboard(lang=get_lang()))
    except Exception:
        await message.answer(translate(get_lang(), 'monitoring_interval_input_error'), reply_markup=monitoring_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('monitoring_autostart'))
async def handle_monitoring_autostart(message: Message):
    current = settings_manager.get_setting('monitoring.auto_start', True)
    value = 'да' if current else 'нет'
    await message.answer(translate(get_lang(), 'monitoring_autostart_prompt', value=value), reply_markup=cancel_keyboard(lang=get_lang()))
    await MonitoringState.waiting_for_autostart.set()

@dp.message_handler(state=MonitoringState.waiting_for_autostart)
async def process_monitoring_autostart(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    if text in ['да', 'yes', 'y', 'oui', 'ja', '是']:
        new_value = True
    elif text in ['нет', 'no', 'n', 'non', 'nein', '否']:
        new_value = False
    else:
        await message.answer(translate(get_lang(), 'input_error'), reply_markup=monitoring_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.set_setting('monitoring.auto_start', new_value):
        status = 'включён' if new_value else 'выключен'
        await message.answer(translate(get_lang(), 'monitoring_autostart_set', status=status), reply_markup=monitoring_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'settings_error'), reply_markup=monitoring_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('monitoring_notify_change'))
async def handle_monitoring_notify_change(message: Message):
    current = settings_manager.get_setting('monitoring.notify_on_change', True)
    value = 'да' if current else 'нет'
    await message.answer(translate(get_lang(), 'monitoring_notify_change_prompt', value=value), reply_markup=cancel_keyboard(lang=get_lang()))
    await MonitoringState.waiting_for_notify_change.set()

@dp.message_handler(state=MonitoringState.waiting_for_notify_change)
async def process_monitoring_notify_change(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    if text in ['да', 'yes', 'y', 'oui', 'ja', '是']:
        new_value = True
    elif text in ['нет', 'no', 'n', 'non', 'nein', '否']:
        new_value = False
    else:
        await message.answer(translate(get_lang(), 'input_error'), reply_markup=monitoring_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.set_setting('monitoring.notify_on_change', new_value):
        status = 'включены' if new_value else 'выключены'
        await message.answer(translate(get_lang(), 'monitoring_notify_change_set', status=status), reply_markup=monitoring_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'settings_error'), reply_markup=monitoring_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('monitoring_notify_start'))
async def handle_monitoring_notify_start(message: Message):
    current = settings_manager.get_setting('monitoring.notify_on_start', True)
    value = 'да' if current else 'нет'
    await message.answer(translate(get_lang(), 'monitoring_notify_start_prompt', value=value), reply_markup=cancel_keyboard(lang=get_lang()))
    await MonitoringState.waiting_for_notify_start.set()

@dp.message_handler(state=MonitoringState.waiting_for_notify_start)
async def process_monitoring_notify_start(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    if text in ['да', 'yes', 'y', 'oui', 'ja', '是']:
        new_value = True
    elif text in ['нет', 'no', 'n', 'non', 'nein', '否']:
        new_value = False
    else:
        await message.answer(translate(get_lang(), 'input_error'), reply_markup=monitoring_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.set_setting('monitoring.notify_on_start', new_value):
        status = 'включены' if new_value else 'выключены'
        await message.answer(translate(get_lang(), 'monitoring_notify_start_set', status=status), reply_markup=monitoring_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'settings_error'), reply_markup=monitoring_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('scan_timeout'))
async def handle_scan_timeout(message: Message):
    current = settings_manager.get_setting('scanning.default_timeout', 5)
    await message.answer(translate(get_lang(), 'scan_timeout_prompt', value=current), reply_markup=cancel_keyboard(lang=get_lang()))
    await ScanSettingsState.waiting_for_timeout.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_timeout)
async def process_scan_timeout(message: Message, state: FSMContext):
    try:
        timeout = int(message.text.strip())
        if timeout < 1 or timeout > 60:
            await message.answer(translate(get_lang(), 'scan_timeout_error'))
            return
        if settings_manager.set_setting('scanning.default_timeout', timeout):
            await message.answer(translate(get_lang(), 'scan_timeout_set', value=timeout))
        else:
            await message.answer(translate(get_lang(), 'scan_timeout_save_error'))
    except Exception:
        await message.answer(translate(get_lang(), 'scan_timeout_input_error'))
    await state.finish()

@dp.message_handler(is_menu_button('scan_max_concurrent'))
async def handle_scan_max_concurrent(message: Message):
    current = settings_manager.get_setting('scanning.max_concurrent_scans', 3)
    await message.answer(translate(get_lang(), 'scan_max_concurrent_prompt', value=current), reply_markup=cancel_keyboard(lang=get_lang()))
    await ScanSettingsState.waiting_for_max_concurrent.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_max_concurrent)
async def process_scan_max_concurrent(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value < 1 or value > 20:
            await message.answer(translate(get_lang(), 'scan_max_concurrent_error'))
            return
        if settings_manager.set_setting('scanning.max_concurrent_scans', value):
            await message.answer(translate(get_lang(), 'scan_max_concurrent_set', value=value))
        else:
            await message.answer(translate(get_lang(), 'scan_max_concurrent_save_error'))
    except Exception:
        await message.answer(translate(get_lang(), 'scan_max_concurrent_input_error'))
    await state.finish()

@dp.message_handler(is_menu_button('scan_ports'))
async def handle_scan_ports(message: Message):
    current = settings_manager.get_setting('scanning.default_ports', [80, 22, 443])
    await message.answer(translate(get_lang(), 'scan_ports_prompt', value=', '.join(map(str, current))), reply_markup=cancel_keyboard(lang=get_lang()))
    await ScanSettingsState.waiting_for_default_ports.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_default_ports)
async def process_scan_ports(message: Message, state: FSMContext):
    ports = parse_ports(message.text)
    if not ports:
        await message.answer(translate(get_lang(), 'scan_ports_error'), reply_markup=scan_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.set_setting('scanning.default_ports', ports):
        await message.answer(translate(get_lang(), 'scan_ports_set', value=', '.join(map(str, ports))), reply_markup=scan_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'scan_ports_save_error'), reply_markup=scan_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('scan_miner_ports'))
async def handle_miner_ports(message: Message):
    current = settings_manager.get_setting('scanning.miner_ports', [4028, 3333])
    await message.answer(translate(get_lang(), 'scan_miner_ports_prompt', value=', '.join(map(str, current))), reply_markup=cancel_keyboard(lang=get_lang()))
    await ScanSettingsState.waiting_for_miner_ports.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_miner_ports)
async def process_miner_ports(message: Message, state: FSMContext):
    ports = parse_ports(message.text)
    if not ports:
        await message.answer(translate(get_lang(), 'scan_miner_ports_error'), reply_markup=scan_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.set_setting('scanning.miner_ports', ports):
        await message.answer(translate(get_lang(), 'scan_miner_ports_set', value=', '.join(map(str, ports))), reply_markup=scan_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'scan_miner_ports_save_error'), reply_markup=scan_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('scan_router_ports'))
async def handle_router_ports(message: Message):
    current = settings_manager.get_setting('scanning.router_ports', [8080, 80, 22])
    await message.answer(translate(get_lang(), 'scan_router_ports_prompt', value=', '.join(map(str, current))), reply_markup=cancel_keyboard(lang=get_lang()))
    await ScanSettingsState.waiting_for_router_ports.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_router_ports)
async def process_router_ports(message: Message, state: FSMContext):
    ports = parse_ports(message.text)
    if not ports:
        await message.answer(translate(get_lang(), 'scan_router_ports_error'), reply_markup=scan_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.set_setting('scanning.router_ports', ports):
        await message.answer(translate(get_lang(), 'scan_router_ports_set', value=', '.join(map(str, ports))), reply_markup=scan_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'scan_router_ports_save_error'), reply_markup=scan_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('scan_ttl'))
async def handle_scan_ttl(message: Message):
    current = settings_manager.get_setting('scanning.results_ttl', 3600)
    await message.answer(translate(get_lang(), 'scan_ttl_prompt', value=current), reply_markup=cancel_keyboard(lang=get_lang()))
    await ScanSettingsState.waiting_for_ttl.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_ttl)
async def process_scan_ttl(message: Message, state: FSMContext):
    try:
        ttl = int(message.text.strip())
        if ttl < 60 or ttl > 604800:  # 7 дней
            await message.answer(translate(get_lang(), 'scan_ttl_error'))
            return
        if settings_manager.set_setting('scanning.results_ttl', ttl):
            await message.answer(translate(get_lang(), 'scan_ttl_set', value=ttl))
        else:
            await message.answer(translate(get_lang(), 'scan_ttl_save_error'))
    except Exception:
        await message.answer(translate(get_lang(), 'scan_ttl_input_error'))
    await state.finish()

def parse_ports(text):
    try:
        return [int(p.strip()) for p in text.split(',') if p.strip().isdigit()]
    except Exception:
        return []

@dp.message_handler(is_menu_button('notifications_toggle'))
async def handle_toggle_notifications(message: Message):
    current = settings_manager.get_setting('notifications.enabled', True)
    value = 'да' if current else 'нет'
    await message.answer(translate(get_lang(), 'notifications_toggle_prompt', value=value), reply_markup=cancel_keyboard(lang=get_lang()))
    await NotificationState.waiting_for_toggle.set()

@dp.message_handler(is_menu_button('quiet_hours'))
async def handle_toggle_quiet_hours(message: Message):
    current = settings_manager.get_setting('notifications.quiet_hours.enabled', False)
    value = 'да' if current else 'нет'
    await message.answer(translate(get_lang(), 'quiet_hours_toggle_prompt', value=value), reply_markup=cancel_keyboard(lang=get_lang()))
    await NotificationState.waiting_for_quiet_toggle.set()

@dp.message_handler(is_menu_button('notifications_level'))
async def handle_notification_level(message: Message):
    current = settings_manager.get_setting('notifications.level', 'INFO')
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('INFO'), KeyboardButton('WARNING'), KeyboardButton('ERROR'))
    keyboard.add(KeyboardButton(translate(get_lang(), 'cancel')))
    await message.answer(translate(get_lang(), 'notifications_level_current', value=current), reply_markup=keyboard)
    await NotificationState.waiting_for_level.set()

@dp.message_handler(is_menu_button('router_ips'))
async def handle_router_ips(message: Message):
    current = settings_manager.get_setting('routers.ips', [])
    current_str = ', '.join(current) if current else 'не задано'
    await message.answer(translate(get_lang(), 'router_ips_prompt', value=current_str), reply_markup=cancel_keyboard(lang=get_lang()))
    await RouterSettingsState.waiting_for_ips.set()

@dp.message_handler(state=RouterSettingsState.waiting_for_ips)
async def process_router_ips(message: Message, state: FSMContext):
    text = message.text.replace('\n', ',').replace(';', ',')
    ips = [ip.strip() for ip in text.split(',') if ip.strip()]
    if not all(validate_ip(ip) for ip in ips):
        await message.answer(translate(get_lang(), 'scan_router_ips_error'), reply_markup=router_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.update_router_ips(ips):
        await message.answer(translate(get_lang(), 'scan_router_ips_set', value=', '.join(ips)), reply_markup=router_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'scan_router_ips_save_error'), reply_markup=router_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('router_interval'))
async def handle_router_interval(message: Message):
    current = settings_manager.get_setting('routers.interval', 300)
    await message.answer(translate(get_lang(), 'router_interval_prompt', value=current), reply_markup=cancel_keyboard(lang=get_lang()))
    await RouterSettingsState.waiting_for_interval.set()

@dp.message_handler(state=RouterSettingsState.waiting_for_interval)
async def process_router_interval(message: Message, state: FSMContext):
    try:
        interval = int(message.text.strip())
        if interval < 10 or interval > 86400:
            await message.answer(translate(get_lang(), 'scan_router_interval_error'), reply_markup=router_menu_keyboard(lang=get_lang()))
            return
        if settings_manager.set_setting('routers.interval', interval):
            await message.answer(translate(get_lang(), 'scan_router_interval_set', value=interval), reply_markup=router_menu_keyboard(lang=get_lang()))
        else:
            await message.answer(translate(get_lang(), 'scan_router_interval_save_error'), reply_markup=router_menu_keyboard(lang=get_lang()))
    except Exception:
        await message.answer(translate(get_lang(), 'scan_router_interval_input_error'), reply_markup=router_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('router_status'))
async def handle_router_status_menu(message: Message):
    statistics_manager.record_command('status_routers')
    await message.answer(translate(get_lang(), 'checking_routers'))
    results = await check_routers_status(ROUTER_IPS, ROUTER_PORTS)
    online_count = sum(1 for r in results if r['status'] == 'online')
    statistics_manager.record_router_check(online_count, len(ROUTER_IPS))
    text = "🌐 *Статус роутеров:*\n\n"
    for r in results:
        emoji = "🟢" if r['status'] == 'online' else "🔴"
        text += f"{emoji} *{r['ip']}*: {r['status']}\n"
        if r['open_ports']:
            text += f"   📡 Порт(ы): {', '.join(map(str, r['open_ports']))}\n"
        text += "\n"
    await message.answer(text, parse_mode='Markdown', reply_markup=main_menu_keyboard(lang=get_lang()))

def validate_ip(ip):
    import re
    return bool(re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', ip))

@dp.message_handler(is_menu_button('interface_language'))
async def handle_interface_language(message: Message):
    current = settings_manager.get_setting('interface.language', 'ru')
    await message.answer(translate(get_lang(), 'interface_language_prompt', value=current), reply_markup=cancel_keyboard(lang=get_lang()))
    await InterfaceSettingsState.waiting_for_language.set()

@dp.message_handler(state=InterfaceSettingsState.waiting_for_language)
async def process_interface_language(message: Message, state: FSMContext):
    lang = message.text.strip().lower()
    if lang not in ['ru', 'en']:
        await message.answer(translate(get_lang(), 'interface_language_error'), reply_markup=interface_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.set_setting('interface.language', lang):
        await message.answer(translate(get_lang(), 'interface_language_set', value=lang), reply_markup=interface_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'interface_language_save_error'), reply_markup=interface_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('interface_progress'))
async def handle_interface_progress(message: Message):
    current = settings_manager.get_setting('interface.show_progress', True)
    value = 'да' if current else 'нет'
    await message.answer(translate(get_lang(), 'interface_progress_prompt', value=value), reply_markup=cancel_keyboard(lang=get_lang()))
    await InterfaceSettingsState.waiting_for_progress.set()

@dp.message_handler(state=InterfaceSettingsState.waiting_for_progress)
async def process_interface_progress(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    if text in ['да', 'yes', 'y', 'oui', 'ja', '是']:
        new_value = True
    elif text in ['нет', 'no', 'n', 'non', 'nein', '否']:
        new_value = False
    else:
        await message.answer(translate(get_lang(), 'input_error'), reply_markup=interface_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.set_setting('interface.show_progress', new_value):
        status = 'включён' if new_value else 'выключен'
        await message.answer(translate(get_lang(), 'interface_progress_set', status=status), reply_markup=interface_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'settings_error'), reply_markup=interface_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('interface_time'))
async def handle_interface_time(message: Message):
    current = settings_manager.get_setting('interface.show_time', True)
    value = 'да' if current else 'нет'
    await message.answer(translate(get_lang(), 'interface_time_prompt', value=value), reply_markup=cancel_keyboard(lang=get_lang()))
    await InterfaceSettingsState.waiting_for_time.set()

@dp.message_handler(state=InterfaceSettingsState.waiting_for_time)
async def process_interface_time(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    if text in ['да', 'yes', 'y', 'oui', 'ja', '是']:
        new_value = True
    elif text in ['нет', 'no', 'n', 'non', 'nein', '否']:
        new_value = False
    else:
        await message.answer(translate(get_lang(), 'input_error'), reply_markup=interface_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.set_setting('interface.show_time', new_value):
        status = 'включён' if new_value else 'выключен'
        await message.answer(translate(get_lang(), 'interface_time_set', status=status), reply_markup=interface_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'settings_error'), reply_markup=interface_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('interface_compact'))
async def handle_interface_compact(message: Message):
    current = settings_manager.get_setting('interface.compact_mode', False)
    value = 'да' if current else 'нет'
    await message.answer(translate(get_lang(), 'interface_compact_prompt', value=value), reply_markup=cancel_keyboard(lang=get_lang()))
    await InterfaceSettingsState.waiting_for_compact.set()

@dp.message_handler(state=InterfaceSettingsState.waiting_for_compact)
async def process_interface_compact(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    if text in ['да', 'yes', 'y', 'oui', 'ja', '是']:
        new_value = True
    elif text in ['нет', 'no', 'n', 'non', 'nein', '否']:
        new_value = False
    else:
        await message.answer(translate(get_lang(), 'input_error'), reply_markup=interface_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.set_setting('interface.compact_mode', new_value):
        status = 'включён' if new_value else 'выключен'
        await message.answer(translate(get_lang(), 'interface_compact_set', status=status), reply_markup=interface_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'settings_error'), reply_markup=interface_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('security_users'))
async def handle_security_users(message: Message):
    current = settings_manager.get_setting('security.allowed_users', [])
    current_str = ', '.join(map(str, current)) if current else 'не задано'
    await message.answer(translate(get_lang(), 'security_users_prompt', value=current_str), reply_markup=cancel_keyboard(lang=get_lang()))
    await SecuritySettingsState.waiting_for_users.set()

@dp.message_handler(state=SecuritySettingsState.waiting_for_users)
async def process_security_users(message: Message, state: FSMContext):
    text = message.text.replace('\n', ',').replace(';', ',')
    users = [u.strip() for u in text.split(',') if u.strip().isdigit()]
    if not users:
        await message.answer(translate(get_lang(), 'security_users_error'), reply_markup=security_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    users = [int(u) for u in users]
    if settings_manager.set_setting('security.allowed_users', users):
        await message.answer(translate(get_lang(), 'security_users_set', value=', '.join(map(str, users))), reply_markup=security_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'security_users_save_error'), reply_markup=security_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('security_admin_only'))
async def handle_security_admin_only(message: Message):
    current = settings_manager.get_setting('security.admin_only', False)
    value = 'да' if current else 'нет'
    await message.answer(translate(get_lang(), 'security_admin_only_prompt', value=value), reply_markup=cancel_keyboard(lang=get_lang()))
    await SecuritySettingsState.waiting_for_admin_only.set()

@dp.message_handler(state=SecuritySettingsState.waiting_for_admin_only)
async def process_security_admin_only(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    if text in ['да', 'yes', 'y', 'oui', 'ja', '是']:
        new_value = True
    elif text in ['нет', 'no', 'n', 'non', 'nein', '否']:
        new_value = False
    else:
        await message.answer(translate(get_lang(), 'input_error'), reply_markup=security_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.set_setting('security.admin_only', new_value):
        status = 'только админ' if new_value else 'все пользователи'
        await message.answer(translate(get_lang(), 'security_admin_only_set', status=status), reply_markup=security_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'settings_error'), reply_markup=security_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('security_log_level'))
async def handle_security_log_level(message: Message):
    current = settings_manager.get_setting('security.log_level', 'INFO')
    await message.answer(translate(get_lang(), 'security_log_level_prompt', value=current), reply_markup=cancel_keyboard(lang=get_lang()))
    await SecuritySettingsState.waiting_for_log_level.set()

@dp.message_handler(state=SecuritySettingsState.waiting_for_log_level)
async def process_security_log_level(message: Message, state: FSMContext):
    level = message.text.strip().upper()
    if level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
        await message.answer(translate(get_lang(), 'security_log_level_error'), reply_markup=security_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.set_setting('security.log_level', level):
        await message.answer(translate(get_lang(), 'security_log_level_set', value=level), reply_markup=security_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'security_log_level_save_error'), reply_markup=security_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('security_token'))
async def handle_security_token(message: Message):
    await message.answer(translate(get_lang(), 'security_token_prompt'), reply_markup=cancel_keyboard(lang=get_lang()))
    await SecuritySettingsState.waiting_for_token.set()

@dp.message_handler(state=SecuritySettingsState.waiting_for_token)
async def process_security_token(message: Message, state: FSMContext):
    token = message.text.strip()
    if not token or len(token) < 30:
        await message.answer(translate(get_lang(), 'security_token_error'), reply_markup=security_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.set_setting('TELEGRAM_BOT_TOKEN', token):
        await message.answer(translate(get_lang(), 'security_token_set'), reply_markup=security_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'security_token_save_error'), reply_markup=security_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('backup_auto'))
async def handle_backup_auto(message: Message):
    current = settings_manager.get_setting('backup.auto', False)
    value = 'да' if current else 'нет'
    await message.answer(translate(get_lang(), 'backup_auto_prompt', value=value), reply_markup=cancel_keyboard(lang=get_lang()))
    await BackupSettingsState.waiting_for_auto.set()

@dp.message_handler(state=BackupSettingsState.waiting_for_auto)
async def process_backup_auto(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    if text in ['да', 'yes', 'y', 'oui', 'ja', '是']:
        new_value = True
    elif text in ['нет', 'no', 'n', 'non', 'nein', '否']:
        new_value = False
    else:
        await message.answer(translate(get_lang(), 'input_error'), reply_markup=backup_menu_keyboard(lang=get_lang()))
        await state.finish()
        return
    if settings_manager.set_setting('backup.auto', new_value):
        status = 'включено' if new_value else 'выключено'
        await message.answer(translate(get_lang(), 'backup_auto_set', status=status), reply_markup=backup_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'settings_error'), reply_markup=backup_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('backup_interval'))
async def handle_backup_interval(message: Message):
    current = settings_manager.get_setting('backup.interval', 24)
    await message.answer(translate(get_lang(), 'backup_interval_prompt', value=current), reply_markup=cancel_keyboard(lang=get_lang()))
    await BackupSettingsState.waiting_for_interval.set()

@dp.message_handler(state=BackupSettingsState.waiting_for_interval)
async def process_backup_interval(message: Message, state: FSMContext):
    try:
        interval = int(message.text.strip())
        if interval < 1 or interval > 168:
            await message.answer(translate(get_lang(), 'backup_interval_error'), reply_markup=backup_menu_keyboard(lang=get_lang()))
            return
        if settings_manager.set_setting('backup.interval', interval):
            await message.answer(translate(get_lang(), 'backup_interval_set', value=interval), reply_markup=backup_menu_keyboard(lang=get_lang()))
        else:
            await message.answer(translate(get_lang(), 'backup_interval_save_error'), reply_markup=backup_menu_keyboard(lang=get_lang()))
    except Exception:
        await message.answer(translate(get_lang(), 'backup_interval_input_error'), reply_markup=backup_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('backup_max_count'))
async def handle_backup_max_count(message: Message):
    current = settings_manager.get_setting('backup.max_count', 10)
    await message.answer(translate(get_lang(), 'backup_max_count_prompt', value=current), reply_markup=cancel_keyboard(lang=get_lang()))
    await BackupSettingsState.waiting_for_max_count.set()

@dp.message_handler(state=BackupSettingsState.waiting_for_max_count)
async def process_backup_max_count(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value < 1 or value > 100:
            await message.answer(translate(get_lang(), 'backup_max_count_error'))
            return
        if settings_manager.set_setting('backup.max_count', value):
            await message.answer(translate(get_lang(), 'backup_max_count_set', value=value), reply_markup=backup_menu_keyboard(lang=get_lang()))
        else:
            await message.answer(translate(get_lang(), 'backup_max_count_save_error'), reply_markup=backup_menu_keyboard(lang=get_lang()))
    except Exception:
        await message.answer(translate(get_lang(), 'backup_max_count_input_error'), reply_markup=backup_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('backup_now'))
async def handle_backup_now(message: Message):
    backup_path = settings_manager.create_backup()
    if backup_path and backup_path.endswith('.zip') and os.path.exists(backup_path):
        with open(backup_path, 'rb') as f:
            await message.answer_document(f, caption=translate(get_lang(), 'backup_created'), reply_markup=backup_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'backup_create_error', value=backup_path), reply_markup=backup_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('export_settings'))
async def handle_export_settings(message: Message):
    json_str = settings_manager.export_settings()
    await message.answer_document(('settings_export.json', json_str.encode('utf-8')), caption=translate(get_lang(), 'settings_exported'), reply_markup=export_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('import_settings'))
async def handle_import_settings(message: Message):
    await message.answer(translate(get_lang(), 'backup_import_prompt'), reply_markup=cancel_keyboard(lang=get_lang()))
    await BackupSettingsState.waiting_for_import.set()

@dp.message_handler(state=BackupSettingsState.waiting_for_import, content_types=ContentType.DOCUMENT)
async def process_import_settings_file(message: Message, state: FSMContext):
    file = message.document
    file_path = os.path.join(UPLOAD_DIR, file.file_name)
    await message.document.download(destination_file=file_path)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json_str = f.read()
        ok = settings_manager.import_settings(json_str)
        if ok:
            await message.answer(translate(get_lang(), 'settings_imported'), reply_markup=export_menu_keyboard(lang=get_lang()))
        else:
            await message.answer(translate(get_lang(), 'settings_import_error'), reply_markup=export_menu_keyboard(lang=get_lang()))
    except Exception as e:
        await message.answer(translate(get_lang(), 'settings_import_error_detail', value=e), reply_markup=export_menu_keyboard(lang=get_lang()))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
    await state.finish()

@dp.message_handler(state=BackupSettingsState.waiting_for_import, content_types=ContentType.TEXT)
async def process_import_settings_text(message: Message, state: FSMContext):
    json_str = message.text.strip()
    ok = settings_manager.import_settings(json_str)
    if ok:
        await message.answer(translate(get_lang(), 'settings_imported'), reply_markup=export_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'settings_import_error'), reply_markup=export_menu_keyboard(lang=get_lang()))
    await state.finish()

@dp.message_handler(is_menu_button('export_stats'))
async def handle_export_stats(message: Message):
    stats_path = os.path.join(UPLOAD_DIR, 'statistics.json')
    if os.path.exists(stats_path):
        with open(stats_path, 'rb') as f:
            await message.answer_document(f, caption=translate(get_lang(), 'statistics_exported'), reply_markup=export_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'statistics_export_error'), reply_markup=export_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('export_logs'))
async def handle_export_logs(message: Message):
    log_path = os.path.join(UPLOAD_DIR, 'bot.log')
    if os.path.exists(log_path):
        with open(log_path, 'rb') as f:
            await message.answer_document(f, caption=translate(get_lang(), 'logs_exported'), reply_markup=export_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'logs_export_error'), reply_markup=export_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('settings_summary'))
async def handle_settings_summary(message: Message):
    # Получаем статус роутеров
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
    await message.answer(summary, parse_mode='Markdown', reply_markup=settings_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('settings_reset'))
async def handle_settings_reset(message: Message):
    ok = settings_manager.reset_to_defaults()
    if ok:
        await message.answer(translate(get_lang(), 'settings_reset'), reply_markup=settings_menu_keyboard(lang=get_lang()))
    else:
        await message.answer(translate(get_lang(), 'settings_reset_error'), reply_markup=settings_menu_keyboard(lang=get_lang()))

@dp.message_handler(is_menu_button('cancel'), state='*')
async def cancel_any_state(message: Message, state: FSMContext):
    await state.finish()
    await message.answer('Действие отменено.', reply_markup=settings_menu_keyboard(lang=get_lang()))

if __name__ == '__main__':
    executor.start_polling(
        dp, 
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    ) 