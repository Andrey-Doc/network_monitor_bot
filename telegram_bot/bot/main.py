import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import Message, ContentType
from .config import TELEGRAM_BOT_TOKEN, CHAT_ID
from .keyboards import main_menu_keyboard
from ..utils.router_monitor import check_routers_status
from ..utils.miner_scan import scan_network_for_miners, scan_miners_from_list
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
import pandas as pd
import os
from ..utils.network_scan import scan_network_devices
import ipaddress

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

ROUTER_IPS = [
    '11.250.0.1',
    '11.250.0.2',
    '11.250.0.3',
    '11.250.0.4',
    '11.250.0.5',
]

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))

class ScanDevicesState(StatesGroup):
    waiting_for_network = State()
    waiting_for_file_request = State()

@dp.message_handler(commands=['start', 'menu'])
async def send_welcome(message: Message):
    await message.answer("Привет! Я бот для мониторинга и сканирования.", reply_markup=main_menu_keyboard())

@dp.message_handler(lambda m: m.text == 'Статус роутеров')
async def handle_router_status(message: Message):
    await message.answer("Проверяю статус роутеров...")
    results = await check_routers_status(ROUTER_IPS)
    text = ""
    for r in results:
        text += f"{r['ip']}: {r['status']} (открытые порты: {', '.join(map(str, r['open_ports'])) if r['open_ports'] else 'нет'})\n"
    await message.answer(text)

@dp.message_handler(lambda m: m.text == 'Сканировать сеть')
async def handle_scan_network(message: Message):
    await message.answer("Введите сеть и маску (например, 192.168.1.0/24):")
    await ScanDevicesState.waiting_for_network.set()

@dp.message_handler(state=ScanDevicesState.waiting_for_network)
async def process_devices_network_input(message: Message, state: FSMContext):
    network = message.text.strip()
    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except Exception:
        await message.answer("Ошибка: некорректный формат сети. Пример: 192.168.1.0/24")
        await state.finish()
        return
    await message.answer(f"Сканирую сеть {network} на устройства...")
    try:
        devices = await scan_network_devices(network)
        if not devices:
            await message.answer("Устройства не найдены.")
            await state.finish()
            return
        text = f"Найдено устройств: {len(devices)}\n"
        for d in devices:
            text += f"{d['ip']}: {d['type']} (открытые порты: {', '.join(map(str, d['open_ports']))})\n"
        text += "\nЕсли хотите получить файл с результатами, напишите 'файл' в ответ."
        await message.answer(text)
        await state.update_data(devices=devices)
        await ScanDevicesState.waiting_for_file_request.set()
    except Exception as e:
        await message.answer(f"Ошибка сканирования: {e}")
        await state.finish()

@dp.message_handler(lambda m: m.text == 'Загрузить файл для сканирования')
async def handle_upload_file(message: Message):
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
        miners = await scan_miners_from_list(ip_list)
        if not miners:
            await message.answer("Майнеры не найдены.")
        else:
            text = "Результаты сканирования:\n"
            for m in miners:
                text += f"{m['ip']}: status={m['status']}, hashrate={m['hashrate']}, uptime={m['uptime']}\n"
            await message.answer(text)
    except Exception as e:
        await message.answer(f"Ошибка обработки файла: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@dp.message_handler(lambda m: m.text == 'Сканировать майнеров')
async def handle_scan_miners(message: Message):
    await message.answer("Введите сеть и маску для поиска майнеров (например, 192.168.1.0/24):")
    await ScanDevicesState.waiting_for_network.set()

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
        df = pd.DataFrame(devices)
        with tempfile.NamedTemporaryFile('w+', suffix='.csv', delete=False) as tmp:
            df.to_csv(tmp.name, index=False)
            tmp.flush()
            await message.answer_document(types.InputFile(tmp.name), caption="Результаты сканирования сети")
        os.remove(tmp.name)
    else:
        await message.answer("Завершено.")
    await state.finish()

@dp.message_handler(state=ScanDevicesState.waiting_for_network)
async def process_miners_network_input(message: Message, state: FSMContext):
    network = message.text.strip()
    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except Exception:
        await message.answer("Ошибка: некорректный формат сети. Пример: 192.168.1.0/24")
        await state.finish()
        return
    await message.answer(f"Сканирую сеть {network} только на майнеры...")
    try:
        miners = await scan_network_for_miners(network)
        if not miners:
            await message.answer("Майнеры не найдены.")
            await state.finish()
            return
        text = "Найдено майнеров: {}\n".format(len(miners))
        for m in miners:
            text += f"{m['ip']}: status={m['status']}, hashrate={m['hashrate']}, uptime={m['uptime']}\n"
        text += "\nЕсли хотите получить файл с результатами, напишите 'файл' в ответ."
        await message.answer(text)
        await state.update_data(miners=miners)
        await ScanDevicesState.waiting_for_file_request.set()
    except Exception as e:
        await message.answer(f"Ошибка сканирования: {e}")
        await state.finish()

async def send_notify_to_owner(text: str):
    await bot.send_message(CHAT_ID, text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True) 