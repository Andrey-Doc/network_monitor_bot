from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        KeyboardButton('Статус роутеров'),
        KeyboardButton('Сканировать сеть'),
    )
    keyboard.add(
        KeyboardButton('Загрузить файл для сканирования'),
        KeyboardButton('Сканировать майнеров'),
    )
    keyboard.add(
        KeyboardButton('Быстрое сканирование сети'),
    )
    return keyboard 