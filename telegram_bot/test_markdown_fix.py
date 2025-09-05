#!/usr/bin/env python3
"""
Тест исправления проблем с Markdown
"""

import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.statistics import StatisticsManager
from utils.markdown_utils import escape_markdown, safe_markdown_text, format_key_value

def test_markdown_escaping():
    """Тестирование экранирования Markdown"""
    print("🧪 Тестирование экранирования Markdown...")
    
    # Тестовые строки с проблемными символами
    test_strings = [
        "Обычный текст",
        "Текст с _подчёркиванием_",
        "Текст с *звёздочками*",
        "Текст с `обратными кавычками`",
        "Текст с [квадратными] скобками",
        "Текст с (круглыми) скобками",
        "Текст с #решёткой",
        "Текст с +плюсом и -минусом",
        "Текст с =равно",
        "Текст с |вертикальной чертой",
        "Текст с {фигурными} скобками",
        "Текст с точкой. И ещё одной.",
        "Текст с !восклицательным знаком!",
    ]
    
    for text in test_strings:
        escaped = escape_markdown(text)
        print(f"Исходный: {text}")
        print(f"Экранированный: {escaped}")
        print("-" * 50)

def test_statistics_report():
    """Тестирование отчёта статистики"""
    print("\n📊 Тестирование отчёта статистики...")
    
    stats = StatisticsManager("test_data")
    
    # Добавляем тестовые данные
    stats.record_command('test_command_with_underscores')
    stats.record_scan('test_scan', 5, 100, 10.5)
    stats.record_router_check(3, 5)
    stats.record_error('test_error', 'Test error message with special chars: _*`[]()')
    
    # Генерируем отчёт
    report = stats.generate_report()
    print("Отчёт статистики:")
    print(report)
    
    # Проверяем длину отчёта
    print(f"\nДлина отчёта: {len(report)} символов")
    
    # Проверяем наличие проблемных символов
    problematic_chars = ['**', '__']
    for char in problematic_chars:
        if char in report:
            print(f"⚠️  Найден проблемный символ: {char}")
        else:
            print(f"✅ Проблемный символ {char} не найден")

def test_formatting_functions():
    """Тестирование функций форматирования"""
    print("\n🎨 Тестирование функций форматирования...")
    
    # Тест safe_markdown_text
    test_text = "Текст с _подчёркиванием_ и *звёздочками*"
    print(f"Исходный текст: {test_text}")
    print(f"Безопасный: {safe_markdown_text(test_text)}")
    print(f"Жирный: {safe_markdown_text(test_text, bold=True)}")
    print(f"Код: {safe_markdown_text(test_text, code=True)}")
    
    # Тест format_key_value
    print(f"Ключ-значение: {format_key_value('test_key', 'test_value')}")
    print(f"Специальные символы: {format_key_value('key_with_underscore', 'value_with_*stars*')}")

if __name__ == '__main__':
    print("🚀 Запуск тестирования исправлений Markdown...\n")
    
    try:
        test_markdown_escaping()
        test_statistics_report()
        test_formatting_functions()
        
        print("\n✅ Все тесты завершены успешно!")
        print("📝 Теперь Markdown должен корректно отображаться в Telegram")
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc() 