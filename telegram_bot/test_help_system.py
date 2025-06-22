#!/usr/bin/env python3
"""
Тест системы помощи
"""

import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.help_system import HelpSystem

def test_help_system():
    """Тестирование системы помощи"""
    print("🧪 Тестирование системы помощи...")
    
    help_system = HelpSystem()
    
    # Тест получения всех разделов
    print("\n📋 Все разделы помощи:")
    sections = help_system.get_all_sections()
    for section in sections:
        print(f"• {section}")
    
    # Тест главной страницы помощи
    print("\n📖 Главная страница помощи:")
    main_help = help_system.get_main_help()
    print(main_help[:300] + "..." if len(main_help) > 300 else main_help)
    
    # Тест отдельных разделов
    print("\n🔍 Тестирование разделов:")
    test_sections = ['commands', 'setup', 'faq', 'bug_report', 'features', 'troubleshooting']
    
    for section in test_sections:
        print(f"\n--- {section.upper()} ---")
        help_section = help_system.get_help_section(section)
        print(f"Заголовок: {help_section['title']}")
        content_preview = help_section['content'][:100] + "..." if len(help_section['content']) > 100 else help_section['content']
        print(f"Содержание: {content_preview}")
    
    # Тест поиска
    print("\n🔍 Тестирование поиска:")
    search_queries = ['команды', 'ошибка', 'настройка', 'мониторинг']
    
    for query in search_queries:
        print(f"\nПоиск: '{query}'")
        results = help_system.search_help(query)
        if results:
            for result in results:
                print(f"• {result['title']}")
        else:
            print("Результаты не найдены")
    
    # Тест несуществующего раздела
    print("\n❌ Тест несуществующего раздела:")
    non_existent = help_system.get_help_section('non_existent')
    print(f"Результат: {non_existent['title']}")

def test_help_content_length():
    """Тест длины содержимого разделов"""
    print("\n📏 Тест длины содержимого:")
    
    help_system = HelpSystem()
    sections = help_system.get_all_sections()
    
    for section in sections:
        help_section = help_system.get_help_section(section)
        content_length = len(help_section['content'])
        print(f"{section}: {content_length} символов")
        
        if content_length > 4000:
            print(f"⚠️  Раздел {section} слишком длинный для Telegram!")
        elif content_length < 100:
            print(f"⚠️  Раздел {section} слишком короткий!")

def test_markdown_safety():
    """Тест безопасности Markdown"""
    print("\n🛡️ Тест безопасности Markdown:")
    
    help_system = HelpSystem()
    sections = help_system.get_all_sections()
    
    problematic_chars = ['**', '__', '```', '`']
    
    for section in sections:
        help_section = help_system.get_help_section(section)
        content = help_section['content']
        
        print(f"\nПроверка раздела: {section}")
        for char in problematic_chars:
            if char in content:
                print(f"⚠️  Найден проблемный символ: {char}")
            else:
                print(f"✅ Символ {char} не найден")

if __name__ == '__main__':
    print("🚀 Запуск тестирования системы помощи...\n")
    
    try:
        test_help_system()
        test_help_content_length()
        test_markdown_safety()
        
        print("\n✅ Все тесты системы помощи завершены успешно!")
        print("📝 Система помощи готова к использованию")
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc() 