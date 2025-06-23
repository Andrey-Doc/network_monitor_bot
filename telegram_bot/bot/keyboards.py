from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        KeyboardButton('Статус роутеров'),
        KeyboardButton('Сканировать сеть'),
    )
    keyboard.add(
        KeyboardButton('Загрузить файл для сканирования'),
        KeyboardButton('Сканировать майнеры'),
    )
    keyboard.add(
        KeyboardButton('Быстрое сканирование сети'),
        KeyboardButton('Статистика'),
    )
    keyboard.add(
        KeyboardButton('Настройки'),
        KeyboardButton('Помощь'),
    )
    return keyboard

def settings_menu_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Мониторинг'), KeyboardButton('Уведомления'))
    kb.add(KeyboardButton('Сканирование'), KeyboardButton('Роутеры'))
    kb.add(KeyboardButton('Интерфейс'), KeyboardButton('Безопасность'))
    kb.add(KeyboardButton('Резервное копирование'), KeyboardButton('Экспорт/Импорт'))
    kb.add(KeyboardButton('Сводка настроек'), KeyboardButton('Сбросить настройки'))
    kb.add(KeyboardButton('Назад в меню'))
    return kb

def monitoring_menu_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Интервал мониторинга'), KeyboardButton('Автозапуск мониторинга'))
    kb.add(KeyboardButton('Уведомления об изменениях'), KeyboardButton('Уведомления при запуске'))
    kb.add(KeyboardButton('Назад к настройкам'))
    return kb

def scan_menu_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Таймаут сканирования'), KeyboardButton('Макс. параллельных сканирований'))
    kb.add(KeyboardButton('Порты для сканирования'), KeyboardButton('Порты майнеров'))
    kb.add(KeyboardButton('Порты роутеров'), KeyboardButton('TTL результатов'))
    kb.add(KeyboardButton('Назад к настройкам'))
    return kb

def notification_menu_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Включить/выключить уведомления'), KeyboardButton('Тихие часы'))
    kb.add(KeyboardButton('Уровни уведомлений'), KeyboardButton('Время тихих часов'))
    kb.add(KeyboardButton('Назад к настройкам'))
    return kb

def router_menu_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('IP адреса роутеров'), KeyboardButton('Порты роутеров'))
    kb.add(KeyboardButton('Интервал проверки'), KeyboardButton('Статус роутеров'))
    kb.add(KeyboardButton('Назад к настройкам'))
    return kb

def interface_menu_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Язык интерфейса'), KeyboardButton('Показывать прогресс'))
    kb.add(KeyboardButton('Показывать время'), KeyboardButton('Компактный режим'))
    kb.add(KeyboardButton('Назад к настройкам'))
    return kb

def security_menu_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Разрешенные пользователи'), KeyboardButton('Только админ настройки'))
    kb.add(KeyboardButton('Уровень логирования'), KeyboardButton('Изменить токен'))
    kb.add(KeyboardButton('Назад к настройкам'))
    return kb

def backup_menu_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Авторезервное копирование'), KeyboardButton('Интервал резервного копирования'))
    kb.add(KeyboardButton('Макс. количество резервных копий'), KeyboardButton('Создать резервную копию сейчас'))
    kb.add(KeyboardButton('Назад к настройкам'))
    return kb

def export_menu_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Экспорт настроек'), KeyboardButton('Импорт настроек'))
    kb.add(KeyboardButton('Экспорт статистики'), KeyboardButton('Экспорт логов'))
    kb.add(KeyboardButton('Назад к настройкам'))
    return kb

def help_menu_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Команды'), KeyboardButton('Настройка'))
    kb.add(KeyboardButton('FAQ'), KeyboardButton('Отчёт об ошибке'))
    kb.add(KeyboardButton('Возможности'), KeyboardButton('Устранение неполадок'))
    kb.add(KeyboardButton('Назад в меню'))
    return kb

def cancel_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Отмена'))
    return kb 