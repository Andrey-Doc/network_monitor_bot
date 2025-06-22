#!/usr/bin/env python3
"""
Запуск Telegram бота для мониторинга и сканирования
"""

import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.main import dp, bot
from aiogram import executor

if __name__ == '__main__':
    print("🚀 Запуск Telegram бота для мониторинга...")
    executor.start_polling(dp, skip_updates=True) 