#!/usr/bin/env python3
"""
Тест системы безопасности бота
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot.utils.settings_manager import SettingsManager

def test_security_system():
    """Тестирует систему безопасности"""
    print("🔒 Тестирование системы безопасности...")
    
    # Инициализируем менеджер настроек
    settings_manager = SettingsManager("data/settings.json")
    
    # Тест 1: Проверка настроек безопасности по умолчанию
    print("\n1. Проверка настроек по умолчанию:")
    allowed_users = settings_manager.get_setting('security.allowed_users', [])
    access_control_enabled = settings_manager.get_setting('security.access_control_enabled', False)
    print(f"   Разрешенные пользователи: {allowed_users}")
    print(f"   Контроль доступа включен: {access_control_enabled}")
    
    # Тест 2: Установка списка пользователей
    print("\n2. Установка списка пользователей:")
    test_users = [123456789, 987654321]
    if settings_manager.set_setting('security.allowed_users', test_users):
        print(f"   ✅ Список пользователей установлен: {test_users}")
    else:
        print("   ❌ Ошибка установки списка пользователей")
    
    # Тест 3: Включение контроля доступа
    print("\n3. Включение контроля доступа:")
    if settings_manager.set_setting('security.access_control_enabled', True):
        print("   ✅ Контроль доступа включен")
    else:
        print("   ❌ Ошибка включения контроля доступа")
    
    # Тест 4: Проверка сохраненных настроек
    print("\n4. Проверка сохраненных настроек:")
    saved_users = settings_manager.get_setting('security.allowed_users', [])
    saved_access_control = settings_manager.get_setting('security.access_control_enabled', False)
    print(f"   Сохраненные пользователи: {saved_users}")
    print(f"   Контроль доступа включен: {saved_access_control}")
    
    # Тест 5: Симуляция проверки доступа
    print("\n5. Симуляция проверки доступа:")
    
    def simulate_check_access(user_id):
        allowed_users = settings_manager.get_setting('security.allowed_users', [])
        access_control_enabled = settings_manager.get_setting('security.access_control_enabled', False)
        
        if not access_control_enabled:
            return True
        if not allowed_users:
            return True
        return user_id in allowed_users
    
    test_cases = [
        (123456789, "Разрешенный пользователь"),
        (987654321, "Разрешенный пользователь"),
        (555666777, "Неразрешенный пользователь"),
        (111222333, "Неразрешенный пользователь")
    ]
    
    for user_id, description in test_cases:
        access_granted = simulate_check_access(user_id)
        status = "✅ Доступ разрешен" if access_granted else "❌ Доступ запрещен"
        print(f"   {description} (ID: {user_id}): {status}")
    
    # Тест 6: Отключение контроля доступа
    print("\n6. Отключение контроля доступа:")
    if settings_manager.set_setting('security.access_control_enabled', False):
        print("   ✅ Контроль доступа отключен")
    else:
        print("   ❌ Ошибка отключения контроля доступа")
    
    # Тест 7: Проверка доступа после отключения
    print("\n7. Проверка доступа после отключения контроля:")
    for user_id, description in test_cases:
        access_granted = simulate_check_access(user_id)
        status = "✅ Доступ разрешен" if access_granted else "❌ Доступ запрещен"
        print(f"   {description} (ID: {user_id}): {status}")
    
    print("\n🎉 Тестирование системы безопасности завершено!")

if __name__ == "__main__":
    test_security_system() 