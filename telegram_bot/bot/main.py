import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import Message, ContentType, CallbackQuery
from .config import TELEGRAM_BOT_TOKEN, CHAT_ID, ROUTER_IPS, ROUTER_PORTS, SCAN_RESULTS_TTL
from .keyboards import main_menu_keyboard
from .inline_keyboards import (
    get_main_inline_keyboard, get_monitoring_control_keyboard, 
    get_scan_options_keyboard, get_settings_keyboard, get_export_keyboard
)
from ..utils.router_monitor import check_routers_status
from ..utils.miner_scan import scan_network_for_miners, scan_miners_from_list
from ..utils.background_monitor import BackgroundMonitor
from ..utils.notifications import NotificationManager, NotificationLevel, NotificationType
from ..utils.statistics import StatisticsManager
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

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))

# Глобальное хранилище результатов сканирования с TTL
scan_results_storage = {}
# Счётчик активных сканирований
active_scans_count = 0

# Инициализация новых модулей
background_monitor = BackgroundMonitor(bot, CHAT_ID)
notification_manager = NotificationManager(bot, CHAT_ID)
statistics_manager = StatisticsManager(UPLOAD_DIR)

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

class ScanMinersState(StatesGroup):
    waiting_for_network = State()
    waiting_for_file_request = State()

class FastScanState(StatesGroup):
    waiting_for_network = State()
    waiting_for_file_request = State()

@dp.message_handler(commands=['start', 'menu'])
async def send_welcome(message: Message):
    statistics_manager.record_command('start')
    await message.answer(
        "Привет! Я бот для мониторинга и сканирования.\n\nВыберите действие:",
        reply_markup=get_main_inline_keyboard()
    )

@dp.callback_query_handler(lambda c: True)
async def process_callback_query(callback_query: CallbackQuery):
    """Обработчик inline-кнопок"""
    data = callback_query.data
    
    if data == "status_routers":
        await callback_query.answer("Проверяю статус роутеров...")
        statistics_manager.record_command('status_routers')
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
        
        await bot.send_message(callback_query.from_user.id, text, parse_mode='Markdown')
        
    elif data == "scan_network":
        await callback_query.answer("Выберите тип сканирования")
        await bot.edit_message_reply_markup(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            reply_markup=get_scan_options_keyboard()
        )
        
    elif data == "scan_full":
        await callback_query.answer("Введите сеть для полного сканирования")
        await bot.send_message(callback_query.from_user.id, "Введите сеть и маску (например, 192.168.1.0/24):")
        await ScanDevicesState.waiting_for_network.set()
        
    elif data == "scan_fast":
        await callback_query.answer("Введите сеть для быстрого сканирования")
        await bot.send_message(callback_query.from_user.id, "Введите сеть и маску для быстрого сканирования:")
        await FastScanState.waiting_for_network.set()
        
    elif data == "scan_miners":
        await callback_query.answer("Введите сеть для поиска майнеров")
        await bot.send_message(callback_query.from_user.id, "Введите сеть и маску для поиска майнеров:")
        await ScanMinersState.waiting_for_network.set()
        
    elif data == "statistics":
        await callback_query.answer("Генерирую отчёт...")
        report = statistics_manager.generate_report()
        await bot.send_message(callback_query.from_user.id, report, parse_mode='Markdown')
        
    elif data == "settings":
        await callback_query.answer("Настройки")
        await bot.edit_message_reply_markup(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            reply_markup=get_settings_keyboard()
        )
        
    elif data == "monitor_start":
        await callback_query.answer("Запускаю мониторинг...")
        await background_monitor.start_monitoring()
        await notification_manager.send_notification(
            level=NotificationLevel.SUCCESS,
            notification_type=NotificationType.SYSTEM_ALERT,
            title="Мониторинг запущен",
            message="Фоновый мониторинг роутеров успешно запущен"
        )
        
    elif data == "monitor_stop":
        await callback_query.answer("Останавливаю мониторинг...")
        await background_monitor.stop_monitoring()
        await notification_manager.send_notification(
            level=NotificationLevel.INFO,
            notification_type=NotificationType.SYSTEM_ALERT,
            title="Мониторинг остановлен",
            message="Фоновый мониторинг роутеров остановлен"
        )
        
    elif data == "monitor_status":
        await callback_query.answer("Статус мониторинга")
        status = "🟢 Активен" if background_monitor.is_running else "🔴 Остановлен"
        await bot.send_message(
            callback_query.from_user.id,
            f"📊 **Статус мониторинга:** {status}"
        )
        
    elif data == "back_to_main":
        await callback_query.answer("Главное меню")
        await bot.edit_message_reply_markup(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            reply_markup=get_main_inline_keyboard()
        )
        
    elif data.startswith("network_"):
        network = data.replace("network_", "")
        await callback_query.answer(f"Выбрана сеть: {network}")
        await bot.send_message(callback_query.from_user.id, f"Сканирую сеть {network}...")
        # Здесь можно добавить логику сканирования
        
    else:
        await callback_query.answer("Функция в разработке")

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
    
    await message.answer(text, parse_mode='Markdown')

@dp.message_handler(lambda m: m.text == 'Сканировать сеть')
async def handle_scan_network(message: Message):
    statistics_manager.record_command('scan_network')
    await message.answer("Введите сеть и маску (например, 192.168.1.0/24):")
    await ScanDevicesState.waiting_for_network.set()

@dp.message_handler(state=ScanDevicesState.waiting_for_network)
async def process_devices_network_input(message: Message, state: FSMContext):
    # Очищаем старые результаты перед новым сканированием
    cleanup_old_results()
    
    global active_scans_count
    active_scans_count += 1
    
    network = message.text.strip()
    start_time = time.time()
    logging.info(f"[SCAN] Запрошено сканирование сети: {network}")
    
    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except Exception as e:
        logging.error(f"[SCAN] Некорректный формат сети: {network}, ошибка: {e}")
        await message.answer("Ошибка: некорректный формат сети. Пример: 192.168.1.0/24")
        active_scans_count -= 1
        await state.finish()
        return
        
    progress_msg = await message.answer(f"Начинаю сканирование сети {network} на устройства... 0%")
    
    async def on_progress(done, total):
        percent = int(done / total * 100)
        bar = '█' * (percent // 10) + '-' * (10 - percent // 10)
        logging.info(f"[SCAN] Прогресс: {done}/{total} ({percent}%)")
        await bot.edit_message_text(
            f"Сканирование: [{bar}] {percent}% ({done}/{total})",
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        
    try:
        logging.info(f"[SCAN] Запуск scan_network_devices({network})")
        devices = await scan_network_devices(network, on_progress=on_progress)
        duration = time.time() - start_time
        
        logging.info(f"[SCAN] Сканирование завершено, найдено устройств: {len(devices)}")
        await bot.edit_message_text(
            f"Сканирование завершено! Найдено устройств: {len(devices)}",
            chat_id=progress_msg.chat.id,
            message_id=progress_msg.message_id
        )
        
        # Записываем статистику
        statistics_manager.record_scan('network', len(devices), net.num_addresses, duration)
        
        # Отправляем уведомление
        await notification_manager.scan_completed('сети', len(devices), duration)
        
        if not devices:
            await message.answer("Устройства не найдены.")
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
        result_msg = await message.answer(text)
        
        # Сохраняем результаты с привязкой к message_id
        scan_results_storage[result_msg.message_id] = {
            'devices': devices,
            'type': 'devices',
            'timestamp': time.time()
        }
        await state.update_data(devices=devices)
        await ScanDevicesState.waiting_for_file_request.set()
        
    except Exception as e:
        logging.error(f"[SCAN] Ошибка сканирования: {e}")
        statistics_manager.record_error('scan_network', str(e))
        await notification_manager.scan_error('сети', str(e))
        
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
    await message.answer("Пожалуйста, отправьте CSV-файл со списком IP-адресов.")

@dp.message_handler(content_types=ContentType.DOCUMENT)
async def process_csv_file(message: Message):
    file = message.document
    if not file.file_name.lower().endswith('.csv'):
        await message.answer("Пожалуйста, отправьте файл в формате CSV.")
        return
        
    file_path = os.path.join(UPLOAD_DIR, file.file_name)
    await message.document.download(destination_file=file_path)
    
    try:
        df = pd.read_csv(file_path)
        if 'ip' not in df.columns:
            await message.answer("В файле должен быть столбец 'ip'.")
            return
            
        ip_list = df['ip'].dropna().astype(str).tolist()
        await message.answer(f"Сканирую {len(ip_list)} адресов из файла...")
        
        start_time = time.time()
        miners = await scan_miners_from_list(ip_list)
        duration = time.time() - start_time
        
        # Записываем статистику
        statistics_manager.record_scan('file_upload', len(miners), len(ip_list), duration)
        
        if not miners:
            await message.answer("Майнеры не найдены.")
        else:
            text = "Результаты сканирования:\n"
            for m in miners:
                text += f"{m['ip']}: status={m['status']}, hashrate={m['hashrate']}, uptime={m['uptime']}\n"
            await message.answer(text)
            
    except Exception as e:
        statistics_manager.record_error('file_processing', str(e))
        await message.answer(f"Ошибка обработки файла: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@dp.message_handler(lambda m: m.text == 'Сканировать майнеры')
async def handle_scan_miners(message: Message):
    statistics_manager.record_command('scan_miners')
    await message.answer("Введите сеть и маску для поиска майнеров (например, 192.168.1.0/24):")
    await ScanMinersState.waiting_for_network.set()

@dp.message_handler(state=ScanDevicesState.waiting_for_file_request)
async def process_devices_file_request(message: Message, state: FSMContext):
    if message.text.strip().lower() == 'файл':
        data = await state.get_data()
        devices = data.get('devices', [])
        if not devices:
            await message.answer("Нет данных для файла.")
            await state.finish()
            return
        import pandas as pd
        import tempfile
        await bot.send_chat_action(message.chat.id, types.ChatActions.UPLOAD_DOCUMENT)
        for d in devices:
            if d.get('type') != 'miner':
                d['type'] = ''
                d['hashrate'] = ''
                d['uptime'] = ''
            else:
                d['hashrate'] = d.get('hashrate', '')
                d['uptime'] = d.get('uptime', '')
        df = pd.DataFrame(devices)
        with tempfile.NamedTemporaryFile('w+', suffix='.csv', delete=False) as tmp:
            df.to_csv(tmp.name, index=False)
            tmp.flush()
            await message.answer_document(types.InputFile(tmp.name), caption="Результаты сканирования сети")
        os.remove(tmp.name)
    else:
        await message.answer("Завершено.")
    await state.finish()

@dp.message_handler(state=ScanMinersState.waiting_for_network)
async def process_miners_network_input(message: Message, state: FSMContext):
    # Очищаем старые результаты перед новым сканированием
    cleanup_old_results()
    
    global active_scans_count
    active_scans_count += 1
    
    network = message.text.strip()
    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except Exception:
        await message.answer("Ошибка: некорректный формат сети. Пример: 192.168.1.0/24")
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
            await message.answer("Майнеры не найдены.")
            active_scans_count -= 1
            await state.finish()
            return
        text = "Найдено майнеров: {}\n".format(len(miners))
        for m in miners:
            text += f"{m['ip']}: miner (hashrate: {m.get('hashrate')}, uptime: {m.get('uptime')})\n"
        text += "\nЕсли хотите получить файл с результатами, напишите 'файл' в ответ или reply на это сообщение."
        result_msg = await message.answer(text)
        # Сохраняем результаты с привязкой к message_id
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

@dp.message_handler(state=ScanMinersState.waiting_for_file_request)
async def process_miners_file_request(message: Message, state: FSMContext):
    if message.text.strip().lower() == 'файл':
        data = await state.get_data()
        miners = data.get('miners', [])
        if not miners:
            await message.answer("Нет данных для файла.")
            await state.finish()
            return
        import pandas as pd
        import tempfile
        await bot.send_chat_action(message.chat.id, types.ChatActions.UPLOAD_DOCUMENT)
        for m in miners:
            m['type'] = 'miner'
            m['hashrate'] = m.get('hashrate', '')
            m['uptime'] = m.get('uptime', '')
        df = pd.DataFrame(miners)
        with tempfile.NamedTemporaryFile('w+', suffix='.csv', delete=False) as tmp:
            df.to_csv(tmp.name, index=False)
            tmp.flush()
            await message.answer_document(types.InputFile(tmp.name), caption="Результаты сканирования майнеров")
        os.remove(tmp.name)
    else:
        await message.answer("Завершено.")
    await state.finish()

@dp.message_handler(lambda m: m.text == 'Быстрое сканирование сети')
async def handle_fast_scan(message: Message):
    await message.answer("Введите сеть и маску для быстрого сканирования (например, 192.168.1.0/24):")
    await FastScanState.waiting_for_network.set()

@dp.message_handler(state=FastScanState.waiting_for_network)
async def process_fast_scan_network_input(message: Message, state: FSMContext):
    # Очищаем старые результаты перед новым сканированием
    cleanup_old_results()
    
    global active_scans_count
    active_scans_count += 1
    
    import ipaddress
    network = message.text.strip()
    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except Exception:
        await message.answer("Ошибка: некорректный формат сети. Пример: 192.168.1.0/24")
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
            await message.answer("Устройства не найдены.")
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
        result_msg = await message.answer(text)
        # Сохраняем результаты с привязкой к message_id
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

@dp.message_handler(state=FastScanState.waiting_for_file_request)
async def process_fast_scan_file_request(message: Message, state: FSMContext):
    if message.text.strip().lower() == 'файл':
        data = await state.get_data()
        devices = data.get('devices', [])
        if not devices:
            await message.answer("Нет данных для файла.")
            await state.finish()
            return
        import pandas as pd
        import tempfile
        await bot.send_chat_action(message.chat.id, types.ChatActions.UPLOAD_DOCUMENT)
        df = pd.DataFrame(devices)
        with tempfile.NamedTemporaryFile('w+', suffix='.csv', delete=False) as tmp:
            df.to_csv(tmp.name, index=False)
            tmp.flush()
            await message.answer_document(types.InputFile(tmp.name), caption="Результаты быстрого сканирования сети")
        os.remove(tmp.name)
    else:
        await message.answer("Завершено.")
    await state.finish()

@dp.message_handler(lambda m: m.reply_to_message and m.text.lower() == 'файл')
async def handle_reply_file_request(message: Message):
    # Очищаем старые результаты перед обработкой
    cleanup_old_results()
    
    reply_msg_id = message.reply_to_message.message_id
    if reply_msg_id in scan_results_storage:
        data = scan_results_storage[reply_msg_id]
        devices = data.get('devices', [])
        miners = data.get('miners', [])
        scan_type = data.get('type', '')
        
        if not devices and not miners:
            await message.answer("Нет данных для файла.")
            return
            
        import pandas as pd
        import tempfile
        await bot.send_chat_action(message.chat.id, types.ChatActions.UPLOAD_DOCUMENT)
        
        if scan_type == 'miners':
            # Обработка результатов сканирования майнеров
            for m in miners:
                m['type'] = 'miner'
                m['hashrate'] = str(m.get('hashrate') or '')
                m['uptime'] = str(m.get('uptime') or '')
            df = pd.DataFrame(miners)
            caption = "Результаты сканирования майнеров"
        else:
            # Обработка результатов сканирования устройств
            for d in devices:
                if d.get('type') != 'miner':
                    d['type'] = ''
                    d['hashrate'] = ''
                    d['uptime'] = ''
                else:
                    d['hashrate'] = str(d.get('hashrate') or '')
                    d['uptime'] = str(d.get('uptime') or '')
            df = pd.DataFrame(devices)
            caption = "Результаты сканирования сети"
            
        with tempfile.NamedTemporaryFile('w+', suffix='.csv', delete=False) as tmp:
            df.to_csv(tmp.name, index=False)
            tmp.flush()
            await message.answer_document(types.InputFile(tmp.name), caption=caption)
        os.remove(tmp.name)
    else:
        await message.answer("Результаты этого сканирования недоступны или устарели. Запустите сканирование заново.")

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

@dp.message_handler(commands=['export_stats'])
async def handle_export_stats(message: Message):
    """Команда для экспорта статистики в CSV"""
    csv_content = statistics_manager.export_csv()
    
    import tempfile
    with tempfile.NamedTemporaryFile('w+', suffix='.csv', delete=False) as tmp:
        tmp.write(csv_content)
        tmp.flush()
        await message.answer_document(
            types.InputFile(tmp.name), 
            caption="📊 Статистика за последние 30 дней"
        )
    os.remove(tmp.name)

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

if __name__ == '__main__':
    executor.start_polling(
        dp, 
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    ) 