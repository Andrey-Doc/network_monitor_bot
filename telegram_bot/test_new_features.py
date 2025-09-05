#!/usr/bin/env python3
"""
Тестирование новых функций бота
"""

import asyncio
import sys
import os
import pytest

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.statistics import StatisticsManager
from utils.notifications import NotificationManager, NotificationLevel, NotificationType

@pytest.mark.asyncio
async def test_statistics():
    """Тестирование системы статистики"""
    print("🧪 Тестирование системы статистики...")
    
    stats = StatisticsManager("test_data")
    
    # Записываем тестовые данные
    stats.record_command('test_command')
    stats.record_scan('test_scan', 5, 100, 10.5)
    stats.record_router_check(3, 5)
    stats.record_error('test_error', 'Test error message')
    
    # Получаем отчёт
    report = stats.generate_report()
    print("📊 Отчёт статистики:")
    print(report)
    
    # Экспортируем в CSV
    csv_data = stats.export_csv()
    print("📄 CSV данные:")
    print(csv_data[:200] + "..." if len(csv_data) > 200 else csv_data)

@pytest.mark.asyncio
async def test_notifications():
    """Тестирование системы уведомлений"""
    print("\n🔔 Тестирование системы уведомлений...")
    
    # Создаём мок-бот для тестирования
    class MockBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            print(f"📤 Отправлено сообщение в {chat_id}:")
            print(f"   {text}")
    
    mock_bot = MockBot()
    notifications = NotificationManager(mock_bot, "test_chat_id")
    
    # Запускаем систему уведомлений
    await notifications.start()
    
    # Отправляем тестовые уведомления
    await notifications.send_notification(
        level=NotificationLevel.INFO,
        notification_type=NotificationType.SYSTEM_ALERT,
        title="Тестовое уведомление",
        message="Это тестовое сообщение для проверки системы уведомлений"
    )
    
    await notifications.router_status_change("192.168.1.1", "online", "offline")
    await notifications.scan_completed("тестовой сети", 10, 5.2)
    await notifications.scan_error("тестового сканирования", "Тестовая ошибка")
    
    # Ждём обработки уведомлений
    await asyncio.sleep(2)
    
    # Останавливаем систему
    await notifications.stop()

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестирования новых функций бота...\n")
    
    try:
        await test_statistics()
        await test_notifications()
        
        print("\n✅ Все тесты завершены успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(main()) 