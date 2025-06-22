#!/usr/bin/env python3
"""
Скрипт для запуска Telegram бота
"""

import sys
import os
import logging
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent))

def main():
    """Основная функция запуска"""
    print("🚀 Запуск Telegram бота для мониторинга и сканирования...")
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log'),
            logging.StreamHandler()
        ]
    )
    
    try:
        # Проверяем наличие конфигурации
        config_path = Path(__file__).parent / "bot" / "config.py"
        if not config_path.exists():
            print("❌ Файл конфигурации не найден!")
            print("Создайте файл telegram_bot/bot/config.py с настройками:")
            print("""
TELEGRAM_BOT_TOKEN = "ваш_токен_бота"
CHAT_ID = ваш_chat_id
ROUTER_IPS = ["11.250.0.1", "11.250.0.2", "11.250.0.3", "11.250.0.4", "11.250.0.5"]
ROUTER_PORTS = [8080, 8022]
SCAN_RESULTS_TTL = 3600
            """)
            return 1
            
        # Создаём директорию для данных
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        
        print("✅ Конфигурация найдена")
        print("✅ Директория данных создана")
        
        # Импортируем и запускаем бота
        from telegram_bot.bot.main import dp, on_startup, on_shutdown
        from aiogram import executor
        
        print("🤖 Запуск бота...")
        print("📱 Бот готов к работе!")
        print("💡 Используйте /start в Telegram для начала работы")
        print("🔧 Используйте /help для получения справки")
        print("⚙️ Используйте кнопку 'Настройки' для конфигурации")
        print("\n" + "="*50)
        
        # Запускаем бота
        executor.start_polling(
            dp,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True
        )
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("Убедитесь, что все зависимости установлены:")
        print("pip install -r requirements.txt")
        return 1
        
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        logging.error(f"Ошибка запуска бота: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 