from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery

def get_main_inline_keyboard():
    """Главное меню с inline-кнопками"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🌐 Статус роутеров", callback_data="status_routers"),
        InlineKeyboardButton("🔍 Сканировать сеть", callback_data="scan_network"),
    )
    keyboard.add(
        InlineKeyboardButton("⛏️ Сканировать майнеры", callback_data="scan_miners"),
        InlineKeyboardButton("⚡ Быстрое сканирование", callback_data="fast_scan"),
    )
    keyboard.add(
        InlineKeyboardButton("📊 Статистика", callback_data="statistics"),
        InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
    )
    keyboard.add(
        InlineKeyboardButton("📋 Помощь", callback_data="help"),
    )
    return keyboard

def get_monitoring_control_keyboard():
    """Кнопки управления мониторингом"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("▶️ Запустить мониторинг", callback_data="monitor_start"),
        InlineKeyboardButton("⏸️ Остановить мониторинг", callback_data="monitor_stop"),
    )
    keyboard.add(
        InlineKeyboardButton("🔄 Статус мониторинга", callback_data="monitor_status"),
        InlineKeyboardButton("⚙️ Настройки мониторинга", callback_data="monitor_settings"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"),
    )
    return keyboard

def get_scan_options_keyboard():
    """Кнопки опций сканирования"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔍 Полное сканирование", callback_data="scan_full"),
        InlineKeyboardButton("⚡ Быстрое сканирование", callback_data="scan_fast"),
    )
    keyboard.add(
        InlineKeyboardButton("🎯 Сканировать майнеры", callback_data="scan_miners_only"),
        InlineKeyboardButton("🌐 Сканировать роутеры", callback_data="scan_routers_only"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"),
    )
    return keyboard

def get_network_input_keyboard():
    """Кнопки для ввода сети"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("192.168.1.0/24", callback_data="network_192.168.1.0/24"),
        InlineKeyboardButton("10.0.0.0/24", callback_data="network_10.0.0.0/24"),
    )
    keyboard.add(
        InlineKeyboardButton("172.16.0.0/24", callback_data="network_172.16.0.0/24"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_scan"),
    )
    return keyboard

def get_settings_keyboard():
    """Кнопки настроек"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("⏰ Интервал мониторинга", callback_data="setting_monitor_interval"),
        InlineKeyboardButton("🔔 Уведомления", callback_data="setting_notifications"),
    )
    keyboard.add(
        InlineKeyboardButton("🌐 Роутеры", callback_data="setting_routers"),
        InlineKeyboardButton("🔍 Порты сканирования", callback_data="setting_ports"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"),
    )
    return keyboard

def get_export_keyboard():
    """Кнопки экспорта данных"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📄 CSV", callback_data="export_csv"),
        InlineKeyboardButton("📊 Excel", callback_data="export_excel"),
    )
    keyboard.add(
        InlineKeyboardButton("📋 JSON", callback_data="export_json"),
        InlineKeyboardButton("📈 График", callback_data="export_chart"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"),
    )
    return keyboard

def get_help_keyboard():
    """Кнопки помощи"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📖 Команды", callback_data="help_commands"),
        InlineKeyboardButton("🔧 Настройка", callback_data="help_setup"),
    )
    keyboard.add(
        InlineKeyboardButton("❓ FAQ", callback_data="help_faq"),
        InlineKeyboardButton("🐛 Отчёт об ошибке", callback_data="help_bug_report"),
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"),
    )
    return keyboard

# Обработчики callback-запросов
async def handle_callback_query(callback_query: CallbackQuery, bot, dp):
    """Обрабатывает нажатия на inline-кнопки"""
    data = callback_query.data
    
    if data == "status_routers":
        await callback_query.answer("Проверяю статус роутеров...")
        # Здесь будет логика проверки статуса
        await bot.send_message(callback_query.from_user.id, "🌐 Проверяю статус роутеров...")
        
    elif data == "scan_network":
        await callback_query.answer("Выберите тип сканирования")
        await bot.edit_message_reply_markup(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            reply_markup=get_scan_options_keyboard()
        )
        
    elif data == "monitor_start":
        await callback_query.answer("Запускаю мониторинг...")
        # Здесь будет логика запуска мониторинга
        
    elif data == "monitor_stop":
        await callback_query.answer("Останавливаю мониторинг...")
        # Здесь будет логика остановки мониторинга
        
    elif data == "back_to_main":
        await callback_query.answer("Возвращаюсь в главное меню")
        await bot.edit_message_reply_markup(
            chat_id=callback_query.from_user.id,
            message_id=callback_query.message.message_id,
            reply_markup=get_main_inline_keyboard()
        )
        
    elif data.startswith("network_"):
        network = data.replace("network_", "")
        await callback_query.answer(f"Выбрана сеть: {network}")
        # Здесь будет логика запуска сканирования выбранной сети
        
    else:
        await callback_query.answer("Функция в разработке") 