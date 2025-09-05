#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы настроек
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_bot.utils.settings_manager import SettingsManager
import json

def test_settings_manager():
    """Тестирует основные функции SettingsManager"""
    print("🧪 Тестирование системы настроек...")
    
    # Создаём временный файл настроек
    test_config_file = "test_settings.json"
    settings_manager = SettingsManager(test_config_file)
    
    try:
        # Тест 1: Загрузка настроек по умолчанию
        print("\n1️⃣ Тест загрузки настроек по умолчанию:")
        default_settings = settings_manager.settings
        print(f"✅ Настройки загружены: {len(default_settings)} разделов")
        
        # Тест 2: Получение настроек
        print("\n2️⃣ Тест получения настроек:")
        monitor_interval = settings_manager.get_setting('monitoring.interval')
        print(f"✅ Интервал мониторинга: {monitor_interval} сек")
        
        router_ips = settings_manager.get_setting('routers.ips')
        print(f"✅ IP роутеров: {router_ips}")
        
        # Тест 3: Изменение настроек
        print("\n3️⃣ Тест изменения настроек:")
        new_interval = 600
        if settings_manager.update_monitoring_interval(new_interval):
            print(f"✅ Интервал изменён на {new_interval} сек")
        else:
            print("❌ Ошибка изменения интервала")
            
        # Проверяем изменение
        updated_interval = settings_manager.get_setting('monitoring.interval')
        if updated_interval == new_interval:
            print(f"✅ Подтверждение: интервал = {updated_interval} сек")
        else:
            print(f"❌ Ошибка: ожидалось {new_interval}, получено {updated_interval}")
            
        # Тест 4: Включение/выключение функций
        print("\n4️⃣ Тест включения/выключения:")
        if settings_manager.toggle_monitoring(False):
            print("✅ Мониторинг выключен")
        else:
            print("❌ Ошибка выключения мониторинга")
            
        if settings_manager.toggle_notifications(True):
            print("✅ Уведомления включены")
        else:
            print("❌ Ошибка включения уведомлений")
            
        # Тест 5: Обновление списков
        print("\n5️⃣ Тест обновления списков:")
        new_router_ips = ['192.168.1.1', '192.168.1.2', '192.168.1.3']
        if settings_manager.update_router_ips(new_router_ips):
            print(f"✅ IP роутеров обновлены: {new_router_ips}")
        else:
            print("❌ Ошибка обновления IP роутеров")
            
        new_ports = [22, 80, 443, 8080]
        if settings_manager.update_scan_ports(new_ports):
            print(f"✅ Порты обновлены: {new_ports}")
        else:
            print("❌ Ошибка обновления портов")
            
        # Тест 6: Сводка настроек
        print("\n6️⃣ Тест сводки настроек:")
        summary = settings_manager.get_settings_summary()
        print("✅ Сводка настроек:")
        print(summary)
        
        # Тест 7: Экспорт настроек
        print("\n7️⃣ Тест экспорта настроек:")
        settings_json = settings_manager.export_settings()
        print(f"✅ Настройки экспортированы ({len(settings_json)} символов)")
        
        # Тест 8: Импорт настроек
        print("\n8️⃣ Тест импорта настроек:")
        test_import_settings = {
            'monitoring': {
                'interval': 120,
                'enabled': True
            },
            'notifications': {
                'enabled': False
            }
        }
        
        if settings_manager.import_settings(json.dumps(test_import_settings)):
            print("✅ Настройки импортированы")
            
            # Проверяем импортированные настройки
            imported_interval = settings_manager.get_setting('monitoring.interval')
            imported_notifications = settings_manager.get_setting('notifications.enabled')
            
            print(f"✅ Импортированный интервал: {imported_interval} сек")
            print(f"✅ Импортированные уведомления: {'включены' if imported_notifications else 'выключены'}")
        else:
            print("❌ Ошибка импорта настроек")
            
        # Тест 9: Сброс настроек
        print("\n9️⃣ Тест сброса настроек:")
        if settings_manager.reset_to_defaults():
            print("✅ Настройки сброшены к значениям по умолчанию")
            
            # Проверяем сброс
            reset_interval = settings_manager.get_setting('monitoring.interval')
            if reset_interval == 300:  # Значение по умолчанию
                print(f"✅ Подтверждение сброса: интервал = {reset_interval} сек")
            else:
                print(f"❌ Ошибка сброса: ожидалось 300, получено {reset_interval}")
        else:
            print("❌ Ошибка сброса настроек")
            
        print("\n🎉 Все тесты завершены!")
        
    except Exception as e:
        print(f"❌ Ошибка во время тестирования: {e}")
        
    finally:
        # Очищаем тестовый файл
        if os.path.exists(test_config_file):
            os.remove(test_config_file)
            print(f"\n🧹 Тестовый файл {test_config_file} удалён")

def test_settings_validation():
    """Тестирует валидацию настроек"""
    print("\n🔍 Тестирование валидации настроек...")
    
    test_config_file = "test_validation.json"
    settings_manager = SettingsManager(test_config_file)
    
    try:
        # Тест некорректных значений
        print("\n1️⃣ Тест некорректных значений:")
        
        # Отрицательный интервал
        if settings_manager.update_monitoring_interval(-100):
            print("❌ Должна быть ошибка для отрицательного интервала")
        else:
            print("✅ Отрицательный интервал отклонён")
            
        # Пустой список IP
        if settings_manager.update_router_ips([]):
            print("❌ Должна быть ошибка для пустого списка IP")
        else:
            print("✅ Пустой список IP отклонён")
            
        # Некорректные порты
        invalid_ports = [70000, -1, 0]  # Некорректные номера портов
        if settings_manager.update_scan_ports(invalid_ports):
            print("❌ Должна быть ошибка для некорректных портов")
        else:
            print("✅ Некорректные порты отклонены")
            
        print("\n✅ Тесты валидации завершены")
        
    except Exception as e:
        print(f"❌ Ошибка валидации: {e}")
        
    finally:
        if os.path.exists(test_config_file):
            os.remove(test_config_file)

def test_settings_persistence():
    """Тестирует сохранение настроек"""
    print("\n💾 Тестирование сохранения настроек...")
    
    test_config_file = "test_persistence.json"
    
    try:
        # Создаём первый экземпляр
        settings_manager1 = SettingsManager(test_config_file)
        settings_manager1.update_monitoring_interval(900)
        settings_manager1.toggle_monitoring(True)
        
        print("✅ Настройки сохранены в первом экземпляре")
        
        # Создаём второй экземпляр и проверяем загрузку
        settings_manager2 = SettingsManager(test_config_file)
        interval = settings_manager2.get_setting('monitoring.interval')
        monitoring_enabled = settings_manager2.get_setting('monitoring.enabled')
        
        if interval == 900 and monitoring_enabled:
            print("✅ Настройки корректно загружены во втором экземпляре")
        else:
            print(f"❌ Ошибка загрузки: интервал={interval}, мониторинг={monitoring_enabled}")
            
        print("\n✅ Тесты сохранения завершены")
        
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        
    finally:
        if os.path.exists(test_config_file):
            os.remove(test_config_file)

if __name__ == "__main__":
    print("🚀 Запуск тестов системы настроек")
    print("=" * 50)
    
    test_settings_manager()
    test_settings_validation()
    test_settings_persistence()
    
    print("\n" + "=" * 50)
    print("✅ Все тесты завершены!") 