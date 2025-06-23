import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import Message, ContentType
from .keyboards import (
    main_menu_keyboard, settings_menu_keyboard, monitoring_menu_keyboard,
    scan_menu_keyboard, notification_menu_keyboard, router_menu_keyboard,
    interface_menu_keyboard, security_menu_keyboard, backup_menu_keyboard,
    export_menu_keyboard, help_menu_keyboard
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

# Глобальное хранилище результатов сканирования с TTL
scan_results_storage = {}
# Счётчик активных сканирований
active_scans_count = 0

# Инициализация новых модулей
background_monitor = BackgroundMonitor(bot, CHAT_ID)
notification_manager = NotificationManager(bot)
statistics_manager = StatisticsManager(UPLOAD_DIR)
help_system = HelpSystem()

# SCAN_RESULTS_TTL: сначала из настроек, потом из config.py
SCAN_RESULTS_TTL = settings_manager.get_setting('scanning.results_ttl') or SCAN_RESULTS_TTL
# DEFAULT_TIMEOUT: сначала из настроек, потом дефолт
DEFAULT_TIMEOUT = settings_manager.get_setting('scanning.default_timeout') or 5

def cleanup_old_results():
    """Очищает старые результаты сканирования"""
    current_time = time.time()
    expired_keys = []
    for msg_id, data in scan_results_storage.items():
        if current_time - data.get('timestamp', 0) > SCAN_RESULTS_TTL:
            expired_keys.append(msg_id)
    
    for key in expired_keys:
        del scan_results_storage[key]
    
    if expired_keys:
        logging.info(f"[CLEANUP] Удалено {len(expired_keys)} старых результатов сканирования")

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

class NotificationState(StatesGroup):
    waiting_for_level = State()
    waiting_for_quiet_start = State()
    waiting_for_quiet_end = State()

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

@dp.message_handler(commands=['start', 'menu'])
async def send_welcome(message: Message):
    statistics_manager.record_command('start')
    await message.answer(
        "Привет! Я бот для мониторинга и сканирования.\n\nВыберите действие:",
        reply_markup=main_menu_keyboard()
    )

@dp.message_handler(lambda m: m.text == 'Настройки')
async def handle_settings_menu(message: Message):
    await message.answer("⚙️ Меню настроек:", reply_markup=settings_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Мониторинг')
async def handle_monitoring_menu(message: Message):
    await message.answer("🌐 Настройки мониторинга:", reply_markup=monitoring_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Сканирование')
async def handle_scan_menu(message: Message):
    await message.answer("🔍 Настройки сканирования:", reply_markup=scan_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Уведомления')
async def handle_notification_menu(message: Message):
    await message.answer("🔔 Настройки уведомлений:", reply_markup=notification_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Роутеры')
async def handle_router_menu(message: Message):
    await message.answer("🌐 Настройки роутеров:", reply_markup=router_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Интерфейс')
async def handle_interface_menu(message: Message):
    await message.answer("🎨 Настройки интерфейса:", reply_markup=interface_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Безопасность')
async def handle_security_menu(message: Message):
    await message.answer("🔒 Настройки безопасности:", reply_markup=security_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Резервное копирование')
async def handle_backup_menu(message: Message):
    await message.answer("💾 Настройки резервного копирования:", reply_markup=backup_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Экспорт/Импорт')
async def handle_export_menu(message: Message):
    await message.answer("📊 Экспорт/Импорт:", reply_markup=export_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Помощь')
async def handle_help_menu(message: Message):
    await message.answer("📋 Справка:", reply_markup=help_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Назад в меню')
async def handle_back_to_main(message: Message):
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Назад к настройкам')
async def handle_back_to_settings(message: Message):
    await message.answer("Меню настроек:", reply_markup=settings_menu_keyboard())

@dp.message_handler(commands=['help'])
async def handle_help_command(message: Message):
    """Команда для получения справки"""
    statistics_manager.record_command('help')
    help_text = help_system.get_main_help()
    await message.answer(
        help_text,
        parse_mode='Markdown',
        reply_markup=help_menu_keyboard()
    )

@dp.message_handler(commands=['status'])
async def handle_status(message: Message):
    active_results = len(scan_results_storage)
    total_routers = len(ROUTER_IPS)
    monitor_status = "🟢 Активен" if background_monitor.is_running else "🔴 Остановлен"
    
    status_text = f"""
🤖 *Статус бота:*
📊 Активных результатов сканирования: `{active_results}`
🔄 Сканирований в процессе: `{active_scans_count}`
🌐 Роутеров в мониторинге: `{total_routers}`
📡 Мониторинг: {monitor_status}
⏰ TTL результатов: `{SCAN_RESULTS_TTL}` сек
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
    await message.answer("✅ Мониторинг роутеров запущен")

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
    await message.answer("⏹️ Мониторинг роутеров остановлен")

async def send_notify_to_owner(text: str):
    await bot.send_message(CHAT_ID, text)

async def on_startup(dp):
    """Функция, выполняемая при запуске бота"""
    logging.info("[STARTUP] Запуск бота...")
    
    # Запускаем систему уведомлений
    await notification_manager.start()
    
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
            await message.answer("❌ Таймаут должен быть от 1 до 60 секунд")
            return
        if settings_manager.set_setting('scanning.default_timeout', timeout):
            await message.answer(f"✅ Таймаут сканирования установлен: `{timeout}` сек", parse_mode='Markdown')
        else:
            await message.answer("❌ Ошибка при сохранении таймаута")
    except Exception:
        await message.answer("❌ Введите целое число (секунды)")
    await state.finish()

@dp.message_handler(lambda m: m.text == 'Статус роутеров')
async def handle_router_status(message: Message):
    statistics_manager.record_command('status_routers')
    await message.answer("Проверяю статус роутеров...")
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
    await message.answer(text, parse_mode='Markdown', reply_markup=main_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Сканировать сеть')
async def handle_scan_network(message: Message):
    statistics_manager.record_command('scan_network')
    await message.answer("Введите сеть и маску (например, 192.168.1.0/24):", reply_markup=scan_menu_keyboard())
    await ScanDevicesState.waiting_for_network.set()

@dp.message_handler(state=ScanDevicesState.waiting_for_network)
async def process_devices_network_input(message: Message, state: FSMContext):
    cleanup_old_results()
    global active_scans_count
    active_scans_count += 1
    network = message.text.strip()
    start_time = time.time()
    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except Exception as e:
        await message.answer("Ошибка: некорректный формат сети. Пример: 192.168.1.0/24", reply_markup=main_menu_keyboard())
        active_scans_count -= 1
        await state.finish()
        return
    progress_msg = await message.answer(f"Начинаю сканирование сети {network} на устройства... 0%")
    async def on_progress(done, total):
        percent = int(done / total * 100)
        bar = '█' * (percent // 10) + '-' * (10 - percent // 10)
        await bot.edit_message_text(
            f"Сканирование: [{bar}] {percent}% ({done}/{total})",
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
    try:
        devices = await scan_network_devices(network, on_progress=on_progress)
        duration = time.time() - start_time
        await bot.edit_message_text(
            f"Сканирование завершено! Найдено устройств: {len(devices)}",
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        statistics_manager.record_scan('network', len(devices), net.num_addresses, duration)
        await notification_manager.scan_completed('сети', len(devices), duration)
        if not devices:
            await message.answer("Устройства не найдены.", reply_markup=main_menu_keyboard())
            active_scans_count -= 1
            await state.finish()
            return
        text = f"Найдено устройств: {len(devices)}\n"
        for d in devices:
            if d.get('type') == 'miner':
                text += f"{d['ip']}: miner (hashrate: {d.get('hashrate')}, uptime: {d.get('uptime')})\n"
            else:
                text += f"{d['ip']}: (открытые порты: {', '.join(map(str, d['open_ports']))})\n"
        text += "\nЕсли хотите получить файл с результатами, напишите 'файл' в ответ или reply на это сообщение."
        result_msg = await message.answer(text, reply_markup=main_menu_keyboard())
        scan_results_storage[result_msg.message_id] = {
            'devices': devices,
            'type': 'devices',
            'timestamp': time.time()
        }
        await state.update_data(devices=devices)
        await ScanDevicesState.waiting_for_file_request.set()
    except Exception as e:
        await bot.edit_message_text(
            f"Ошибка сканирования: {e}",
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        active_scans_count -= 1
        await state.finish()

@dp.message_handler(lambda m: m.text == 'Загрузить файл для сканирования')
async def handle_upload_file(message: Message):
    statistics_manager.record_command('upload_file')
    await message.answer("Пожалуйста, отправьте CSV-файл со списком IP-адресов.", reply_markup=main_menu_keyboard())

@dp.message_handler(content_types=ContentType.DOCUMENT)
async def process_csv_file(message: Message):
    file = message.document
    if not file.file_name.lower().endswith('.csv'):
        await message.answer("Пожалуйста, отправьте файл в формате CSV.", reply_markup=main_menu_keyboard())
        return
    file_path = os.path.join(UPLOAD_DIR, file.file_name)
    await message.document.download(destination_file=file_path)
    try:
        df = pd.read_csv(file_path)
        if 'ip' not in df.columns:
            await message.answer("В файле должен быть столбец 'ip'.", reply_markup=main_menu_keyboard())
            return
        ip_list = df['ip'].dropna().astype(str).tolist()
        await message.answer(f"Сканирую {len(ip_list)} адресов из файла...", reply_markup=main_menu_keyboard())
        start_time = time.time()
        miners = await scan_miners_from_list(ip_list)
        duration = time.time() - start_time
        statistics_manager.record_scan('file_upload', len(miners), len(ip_list), duration)
        if not miners:
            await message.answer("Майнеры не найдены.", reply_markup=main_menu_keyboard())
        else:
            text = "Результаты сканирования:\n"
            for m in miners:
                text += f"{m['ip']}: status={m['status']}, hashrate={m['hashrate']}, uptime={m['uptime']}\n"
            await message.answer(text, reply_markup=main_menu_keyboard())
    except Exception as e:
        statistics_manager.record_error('file_processing', str(e))
        await message.answer(f"Ошибка обработки файла: {e}", reply_markup=main_menu_keyboard())
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@dp.message_handler(lambda m: m.text == 'Сканировать майнеры')
async def handle_scan_miners(message: Message):
    statistics_manager.record_command('scan_miners')
    await message.answer("Введите сеть и маску для поиска майнеров (например, 192.168.1.0/24):", reply_markup=scan_menu_keyboard())
    await ScanMinersState.waiting_for_network.set()

@dp.message_handler(state=ScanMinersState.waiting_for_network)
async def process_miners_network_input(message: Message, state: FSMContext):
    cleanup_old_results()
    global active_scans_count
    active_scans_count += 1
    network = message.text.strip()
    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except Exception:
        await message.answer("Ошибка: некорректный формат сети. Пример: 192.168.1.0/24", reply_markup=main_menu_keyboard())
        active_scans_count -= 1
        await state.finish()
        return
    progress_msg = await message.answer(f"Начинаю сканирование сети {network} только на майнеры... 0%")
    async def on_progress(done, total):
        percent = int(done / total * 100)
        bar = '█' * (percent // 10) + '-' * (10 - percent // 10)
        await bot.edit_message_text(
            f"Сканирование: [{bar}] {percent}% ({done}/{total})",
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
    try:
        miners = await scan_network_for_miners(network, on_progress=on_progress)
        await bot.edit_message_text(
            f"Сканирование завершено! Найдено майнеров: {len(miners)}",
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        if not miners:
            await message.answer("Майнеры не найдены.", reply_markup=main_menu_keyboard())
            active_scans_count -= 1
            await state.finish()
            return
        text = "Найдено майнеров: {}\n".format(len(miners))
        for m in miners:
            text += f"{m['ip']}: miner (hashrate: {m.get('hashrate')}, uptime: {m.get('uptime')})\n"
        text += "\nЕсли хотите получить файл с результатами, напишите 'файл' в ответ или reply на это сообщение."
        result_msg = await message.answer(text, reply_markup=main_menu_keyboard())
        scan_results_storage[result_msg.message_id] = {
            'miners': miners,
            'type': 'miners',
            'timestamp': time.time()
        }
        await state.update_data(miners=miners)
        await ScanMinersState.waiting_for_file_request.set()
    except Exception as e:
        await bot.edit_message_text(
            f"Ошибка сканирования: {e}",
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        active_scans_count -= 1
        await state.finish()

@dp.message_handler(lambda m: m.text == 'Быстрое сканирование сети')
async def handle_fast_scan(message: Message):
    await message.answer("Введите сеть и маску для быстрого сканирования (например, 192.168.1.0/24):", reply_markup=scan_menu_keyboard())
    await FastScanState.waiting_for_network.set()

@dp.message_handler(state=FastScanState.waiting_for_network)
async def process_fast_scan_network_input(message: Message, state: FSMContext):
    cleanup_old_results()
    global active_scans_count
    active_scans_count += 1
    network = message.text.strip()
    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except Exception:
        await message.answer("Ошибка: некорректный формат сети. Пример: 192.168.1.0/24", reply_markup=main_menu_keyboard())
        active_scans_count -= 1
        await state.finish()
        return
    progress_msg = await message.answer(f"Начинаю быстрое сканирование сети {network}... 0%")
    async def on_progress(done, total):
        percent = int(done / total * 100)
        bar = '█' * (percent // 10) + '-' * (10 - percent // 10)
        await bot.edit_message_text(
            f"Быстрое сканирование: [{bar}] {percent}% ({done}/{total})",
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
    try:
        devices = await fast_scan_network(network, on_progress=on_progress)
        await bot.edit_message_text(
            f"Быстрое сканирование завершено! Найдено устройств: {len(devices)}",
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        if not devices:
            await message.answer("Устройства не найдены.", reply_markup=main_menu_keyboard())
            active_scans_count -= 1
            await state.finish()
            return
        text = f"Найдено устройств: {len(devices)}\n"
        for d in devices:
            if d.get('type') == 'miner':
                text += f"{d['ip']}: miner (hashrate: {d.get('hashrate')}, uptime: {d.get('uptime')})\n"
            else:
                text += f"{d['ip']}: {d.get('type', 'unknown')} (открытые порты: {', '.join(map(str, d['open_ports']))})\n"
        text += "\nЕсли хотите получить файл с результатами, напишите 'файл' в ответ или reply на это сообщение."
        result_msg = await message.answer(text, reply_markup=main_menu_keyboard())
        scan_results_storage[result_msg.message_id] = {
            'devices': devices,
            'type': 'fast_scan',
            'timestamp': time.time()
        }
        await state.update_data(devices=devices)
        await FastScanState.waiting_for_file_request.set()
    except Exception as e:
        await bot.edit_message_text(
            f"Ошибка быстрого сканирования: {e}",
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        active_scans_count -= 1
        await state.finish()

@dp.message_handler(lambda m: m.text == 'Статистика')
async def handle_statistics(message: Message):
    report = statistics_manager.generate_report()
    await message.answer(report, parse_mode='Markdown', reply_markup=main_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Интервал мониторинга')
async def handle_monitoring_interval(message: Message):
    current = settings_manager.get_setting('monitoring.interval', 300)
    await message.answer(f'Текущий интервал мониторинга: {current} сек.\nВведите новый интервал в секундах:', reply_markup=types.ReplyKeyboardRemove())
    await MonitoringState.waiting_for_interval.set()

@dp.message_handler(state=MonitoringState.waiting_for_interval)
async def process_monitoring_interval(message: Message, state: FSMContext):
    try:
        interval = int(message.text.strip())
        if interval < 10 or interval > 86400:
            await message.answer('❌ Интервал должен быть от 10 до 86400 секунд.')
            return
        if settings_manager.set_setting('monitoring.interval', interval):
            await message.answer(f'✅ Интервал мониторинга установлен: {interval} сек', reply_markup=monitoring_menu_keyboard())
        else:
            await message.answer('❌ Ошибка при сохранении интервала.', reply_markup=monitoring_menu_keyboard())
    except Exception:
        await message.answer('❌ Введите целое число (секунды).', reply_markup=monitoring_menu_keyboard())
    await state.finish()

@dp.message_handler(lambda m: m.text == 'Автозапуск мониторинга')
async def handle_monitoring_autostart(message: Message):
    current = settings_manager.get_setting('monitoring.auto_start', False)
    new_value = not current
    if settings_manager.set_setting('monitoring.auto_start', new_value):
        status = 'включён' if new_value else 'выключен'
        await message.answer(f'Автозапуск мониторинга теперь {status}.', reply_markup=monitoring_menu_keyboard())
    else:
        await message.answer('❌ Ошибка при изменении автозапуска.', reply_markup=monitoring_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Уведомления об изменениях')
async def handle_monitoring_notify_change(message: Message):
    current = settings_manager.get_setting('monitoring.notify_on_change', False)
    new_value = not current
    if settings_manager.set_setting('monitoring.notify_on_change', new_value):
        status = 'включены' if new_value else 'выключены'
        await message.answer(f'Уведомления об изменениях теперь {status}.', reply_markup=monitoring_menu_keyboard())
    else:
        await message.answer('❌ Ошибка при изменении уведомлений.', reply_markup=monitoring_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Уведомления при запуске')
async def handle_monitoring_notify_start(message: Message):
    current = settings_manager.get_setting('monitoring.notify_on_start', False)
    new_value = not current
    if settings_manager.set_setting('monitoring.notify_on_start', new_value):
        status = 'включены' if new_value else 'выключены'
        await message.answer(f'Уведомления при запуске теперь {status}.', reply_markup=monitoring_menu_keyboard())
    else:
        await message.answer('❌ Ошибка при изменении уведомлений.', reply_markup=monitoring_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Включить/выключить уведомления')
async def handle_toggle_notifications(message: Message):
    current = settings_manager.get_setting('notifications.enabled', True)
    new_value = not current
    if settings_manager.set_setting('notifications.enabled', new_value):
        status = 'включены' if new_value else 'выключены'
        await message.answer(f'Уведомления теперь {status}.', reply_markup=notification_menu_keyboard())
    else:
        await message.answer('❌ Ошибка при изменении уведомлений.', reply_markup=notification_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Тихие часы')
async def handle_toggle_quiet_hours(message: Message):
    current = settings_manager.get_setting('notifications.quiet_hours.enabled', False)
    new_value = not current
    if settings_manager.set_setting('notifications.quiet_hours.enabled', new_value):
        status = 'включены' if new_value else 'выключены'
        await message.answer(f'Тихие часы теперь {status}.', reply_markup=notification_menu_keyboard())
    else:
        await message.answer('❌ Ошибка при изменении тихих часов.', reply_markup=notification_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Уровни уведомлений')
async def handle_notification_level(message: Message):
    current = settings_manager.get_setting('notifications.level', 'INFO')
    await message.answer(f'Текущий уровень уведомлений: {current}\nВведите новый уровень (INFO, WARNING, ERROR):', reply_markup=types.ReplyKeyboardRemove())
    await NotificationState.waiting_for_level.set()

@dp.message_handler(state=NotificationState.waiting_for_level)
async def process_notification_level(message: Message, state: FSMContext):
    level = message.text.strip().upper()
    if level not in ['INFO', 'WARNING', 'ERROR']:
        await message.answer('❌ Допустимые значения: INFO, WARNING, ERROR.')
        return
    if settings_manager.set_setting('notifications.level', level):
        await message.answer(f'✅ Уровень уведомлений установлен: {level}', reply_markup=notification_menu_keyboard())
    else:
        await message.answer('❌ Ошибка при сохранении уровня.', reply_markup=notification_menu_keyboard())
    await state.finish()

@dp.message_handler(lambda m: m.text == 'Время тихих часов')
async def handle_quiet_hours_time(message: Message, state: FSMContext):
    current_start = settings_manager.get_setting('notifications.quiet_hours.start', '22:00')
    current_end = settings_manager.get_setting('notifications.quiet_hours.end', '08:00')
    await message.answer(f'Текущее время тихих часов: {current_start} — {current_end}\nВведите время начала (чч:мм):', reply_markup=types.ReplyKeyboardRemove())
    await NotificationState.waiting_for_quiet_start.set()

@dp.message_handler(state=NotificationState.waiting_for_quiet_start)
async def process_quiet_hours_start(message: Message, state: FSMContext):
    start = message.text.strip()
    if not validate_time(start):
        await message.answer('❌ Введите время в формате чч:мм (например, 22:00).')
        return
    await state.update_data(quiet_start=start)
    await message.answer('Введите время окончания (чч:мм):')
    await NotificationState.waiting_for_quiet_end.set()

@dp.message_handler(state=NotificationState.waiting_for_quiet_end)
async def process_quiet_hours_end(message: Message, state: FSMContext):
    end = message.text.strip()
    if not validate_time(end):
        await message.answer('❌ Введите время в формате чч:мм (например, 08:00).')
        return
    data = await state.get_data()
    start = data.get('quiet_start', '22:00')
    ok1 = settings_manager.set_setting('notifications.quiet_hours.start', start)
    ok2 = settings_manager.set_setting('notifications.quiet_hours.end', end)
    if ok1 and ok2:
        await message.answer(f'✅ Время тихих часов установлено: {start} — {end}', reply_markup=notification_menu_keyboard())
    else:
        await message.answer('❌ Ошибка при сохранении времени.', reply_markup=notification_menu_keyboard())
    await state.finish()

def validate_time(s):
    import re
    return bool(re.match(r'^[0-2][0-9]:[0-5][0-9]$', s))

@dp.message_handler(lambda m: m.text == 'Таймаут сканирования')
async def handle_scan_timeout(message: Message):
    current = settings_manager.get_setting('scanning.default_timeout', 5)
    await message.answer(f'Текущий таймаут: {current} сек.\nВведите новый таймаут (1-60 сек):', reply_markup=types.ReplyKeyboardRemove())
    await ScanSettingsState.waiting_for_timeout.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_timeout)
async def process_scan_timeout(message: Message, state: FSMContext):
    try:
        timeout = int(message.text.strip())
        if timeout < 1 or timeout > 60:
            await message.answer('❌ Таймаут должен быть от 1 до 60 секунд.')
            return
        if settings_manager.set_setting('scanning.default_timeout', timeout):
            await message.answer(f'✅ Таймаут сканирования установлен: {timeout} сек', reply_markup=scan_menu_keyboard())
        else:
            await message.answer('❌ Ошибка при сохранении таймаута.', reply_markup=scan_menu_keyboard())
    except Exception:
        await message.answer('❌ Введите целое число (секунды).', reply_markup=scan_menu_keyboard())
    await state.finish()

@dp.message_handler(lambda m: m.text == 'Макс. параллельных сканирований')
async def handle_scan_max_concurrent(message: Message):
    current = settings_manager.get_setting('scanning.max_concurrent_scans', 3)
    await message.answer(f'Текущее максимальное число параллельных сканирований: {current}\nВведите новое значение (1-20):', reply_markup=types.ReplyKeyboardRemove())
    await ScanSettingsState.waiting_for_max_concurrent.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_max_concurrent)
async def process_scan_max_concurrent(message: Message, state: FSMContext):
    try:
        value = int(message.text.strip())
        if value < 1 or value > 20:
            await message.answer('❌ Значение должно быть от 1 до 20.')
            return
        if settings_manager.set_setting('scanning.max_concurrent_scans', value):
            await message.answer(f'✅ Максимальное число параллельных сканирований: {value}', reply_markup=scan_menu_keyboard())
        else:
            await message.answer('❌ Ошибка при сохранении.', reply_markup=scan_menu_keyboard())
    except Exception:
        await message.answer('❌ Введите целое число.', reply_markup=scan_menu_keyboard())
    await state.finish()

@dp.message_handler(lambda m: m.text == 'Порты для сканирования')
async def handle_scan_ports(message: Message):
    current = settings_manager.get_setting('scanning.default_ports', [80, 22, 443])
    await message.answer(f'Текущие порты: {", ".join(map(str, current))}\nВведите новые порты через запятую:', reply_markup=types.ReplyKeyboardRemove())
    await ScanSettingsState.waiting_for_default_ports.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_default_ports)
async def process_scan_ports(message: Message, state: FSMContext):
    ports = parse_ports(message.text)
    if not ports:
        await message.answer('❌ Введите список портов через запятую, например: 80,22,443', reply_markup=scan_menu_keyboard())
        await state.finish()
        return
    if settings_manager.set_setting('scanning.default_ports', ports):
        await message.answer(f'✅ Порты для сканирования установлены: {", ".join(map(str, ports))}', reply_markup=scan_menu_keyboard())
    else:
        await message.answer('❌ Ошибка при сохранении портов.', reply_markup=scan_menu_keyboard())
    await state.finish()

@dp.message_handler(lambda m: m.text == 'Порты майнеров')
async def handle_miner_ports(message: Message):
    current = settings_manager.get_setting('scanning.miner_ports', [4028, 3333])
    await message.answer(f'Текущие порты майнеров: {", ".join(map(str, current))}\nВведите новые порты через запятую:', reply_markup=types.ReplyKeyboardRemove())
    await ScanSettingsState.waiting_for_miner_ports.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_miner_ports)
async def process_miner_ports(message: Message, state: FSMContext):
    ports = parse_ports(message.text)
    if not ports:
        await message.answer('❌ Введите список портов через запятую, например: 4028,3333', reply_markup=scan_menu_keyboard())
        await state.finish()
        return
    if settings_manager.set_setting('scanning.miner_ports', ports):
        await message.answer(f'✅ Порты майнеров установлены: {", ".join(map(str, ports))}', reply_markup=scan_menu_keyboard())
    else:
        await message.answer('❌ Ошибка при сохранении портов.', reply_markup=scan_menu_keyboard())
    await state.finish()

@dp.message_handler(lambda m: m.text == 'Порты роутеров')
async def handle_router_ports(message: Message):
    current = settings_manager.get_setting('scanning.router_ports', [8080, 80, 22])
    await message.answer(f'Текущие порты роутеров: {", ".join(map(str, current))}\nВведите новые порты через запятую:', reply_markup=types.ReplyKeyboardRemove())
    await ScanSettingsState.waiting_for_router_ports.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_router_ports)
async def process_router_ports(message: Message, state: FSMContext):
    ports = parse_ports(message.text)
    if not ports:
        await message.answer('❌ Введите список портов через запятую, например: 8080,80,22', reply_markup=scan_menu_keyboard())
        await state.finish()
        return
    if settings_manager.set_setting('scanning.router_ports', ports):
        await message.answer(f'✅ Порты роутеров установлены: {", ".join(map(str, ports))}', reply_markup=scan_menu_keyboard())
    else:
        await message.answer('❌ Ошибка при сохранении портов.', reply_markup=scan_menu_keyboard())
    await state.finish()

@dp.message_handler(lambda m: m.text == 'TTL результатов')
async def handle_scan_ttl(message: Message):
    current = settings_manager.get_setting('scanning.results_ttl', 3600)
    await message.answer(f'Текущий TTL результатов: {current} сек.\nВведите новый TTL (60-86400 сек):', reply_markup=types.ReplyKeyboardRemove())
    await ScanSettingsState.waiting_for_ttl.set()

@dp.message_handler(state=ScanSettingsState.waiting_for_ttl)
async def process_scan_ttl(message: Message, state: FSMContext):
    try:
        ttl = int(message.text.strip())
        if ttl < 60 or ttl > 86400:
            await message.answer('❌ TTL должен быть от 60 до 86400 секунд.')
            return
        if settings_manager.set_setting('scanning.results_ttl', ttl):
            await message.answer(f'✅ TTL результатов установлен: {ttl} сек', reply_markup=scan_menu_keyboard())
        else:
            await message.answer('❌ Ошибка при сохранении TTL.', reply_markup=scan_menu_keyboard())
    except Exception:
        await message.answer('❌ Введите целое число (секунды).', reply_markup=scan_menu_keyboard())
    await state.finish()

def parse_ports(text):
    try:
        return [int(p.strip()) for p in text.split(',') if p.strip().isdigit()]
    except Exception:
        return []

@dp.message_handler(lambda m: m.text == 'IP адреса роутеров')
async def handle_router_ips(message: Message):
    current = settings_manager.get_setting('routers.ips', [])
    current_str = ', '.join(current) if current else 'не задано'
    await message.answer(f'Текущие IP адреса роутеров: {current_str}\nВведите новые IP через запятую или с новой строки:', reply_markup=types.ReplyKeyboardRemove())
    await RouterSettingsState.waiting_for_ips.set()

@dp.message_handler(state=RouterSettingsState.waiting_for_ips)
async def process_router_ips(message: Message, state: FSMContext):
    text = message.text.replace('\n', ',').replace(';', ',')
    ips = [ip.strip() for ip in text.split(',') if ip.strip()]
    if not all(validate_ip(ip) for ip in ips):
        await message.answer('❌ Введите корректные IP-адреса через запятую или с новой строки.', reply_markup=router_menu_keyboard())
        await state.finish()
        return
    if settings_manager.update_router_ips(ips):
        await message.answer(f'✅ IP адреса роутеров обновлены: {", ".join(ips)}', reply_markup=router_menu_keyboard())
    else:
        await message.answer('❌ Ошибка при сохранении IP.', reply_markup=router_menu_keyboard())
    await state.finish()

@dp.message_handler(lambda m: m.text == 'Порты роутеров')
async def handle_router_ports_setting(message: Message):
    current = settings_manager.get_setting('routers.ports', [8080, 80, 22])
    await message.answer(f'Текущие порты роутеров: {", ".join(map(str, current))}\nВведите новые порты через запятую:', reply_markup=types.ReplyKeyboardRemove())
    await RouterSettingsState.waiting_for_ports.set()

@dp.message_handler(state=RouterSettingsState.waiting_for_ports)
async def process_router_ports_setting(message: Message, state: FSMContext):
    ports = parse_ports(message.text)
    if not ports:
        await message.answer('❌ Введите список портов через запятую, например: 8080,80,22', reply_markup=router_menu_keyboard())
        await state.finish()
        return
    if settings_manager.update_router_ports(ports):
        await message.answer(f'✅ Порты роутеров обновлены: {", ".join(map(str, ports))}', reply_markup=router_menu_keyboard())
    else:
        await message.answer('❌ Ошибка при сохранении портов.', reply_markup=router_menu_keyboard())
    await state.finish()

@dp.message_handler(lambda m: m.text == 'Интервал проверки')
async def handle_router_interval(message: Message):
    current = settings_manager.get_setting('routers.interval', 300)
    await message.answer(f'Текущий интервал проверки роутеров: {current} сек.\nВведите новый интервал (10-86400 сек):', reply_markup=types.ReplyKeyboardRemove())
    await RouterSettingsState.waiting_for_interval.set()

@dp.message_handler(state=RouterSettingsState.waiting_for_interval)
async def process_router_interval(message: Message, state: FSMContext):
    try:
        interval = int(message.text.strip())
        if interval < 10 or interval > 86400:
            await message.answer('❌ Интервал должен быть от 10 до 86400 секунд.', reply_markup=router_menu_keyboard())
            return
        if settings_manager.set_setting('routers.interval', interval):
            await message.answer(f'✅ Интервал проверки роутеров установлен: {interval} сек', reply_markup=router_menu_keyboard())
        else:
            await message.answer('❌ Ошибка при сохранении интервала.', reply_markup=router_menu_keyboard())
    except Exception:
        await message.answer('❌ Введите целое число (секунды).', reply_markup=router_menu_keyboard())
    await state.finish()

@dp.message_handler(lambda m: m.text == 'Статус роутеров')
async def handle_router_status_menu(message: Message):
    statistics_manager.record_command('status_routers')
    await message.answer("Проверяю статус роутеров...")
    ips = settings_manager.get_setting('routers.ips', [])
    ports = settings_manager.get_setting('routers.ports', [])
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
    await message.answer(text, parse_mode='Markdown', reply_markup=router_menu_keyboard())

def validate_ip(ip):
    import re
    return bool(re.match(r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', ip))

if __name__ == '__main__':
    executor.start_polling(
        dp, 
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    ) 