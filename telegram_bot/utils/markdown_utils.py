"""
Утилиты для безопасной работы с Markdown в Telegram
"""

def escape_markdown(text: str) -> str:
    """
    Экранирует специальные символы Markdown для безопасного отображения в Telegram
    
    Args:
        text: Исходный текст
        
    Returns:
        Текст с экранированными символами
    """
    if not text:
        return text
        
    # Символы, которые нужно экранировать в Markdown
    escape_chars = ['_', '*', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def safe_markdown_text(text: str, bold: bool = False, italic: bool = False, code: bool = False) -> str:
    """
    Создаёт безопасный Markdown текст с заданным форматированием
    
    Args:
        text: Исходный текст
        bold: Жирный шрифт
        italic: Курсив
        code: Код
        
    Returns:
        Отформатированный текст
    """
    if not text:
        return text
    
    # Экранируем специальные символы
    safe_text = escape_markdown(text)
    
    # Применяем форматирование
    if code:
        return f"`{safe_text}`"
    elif bold and italic:
        return f"*__{safe_text}__*"
    elif bold:
        return f"*{safe_text}*"
    elif italic:
        return f"_{safe_text}_"
    else:
        return safe_text

def format_list_item(text: str, bullet: str = "•") -> str:
    """
    Форматирует элемент списка с безопасным Markdown
    
    Args:
        text: Текст элемента
        bullet: Маркер списка
        
    Returns:
        Отформатированный элемент списка
    """
    return f"{bullet} {escape_markdown(text)}"

def format_key_value(key: str, value, bullet: str = "•") -> str:
    """
    Форматирует пару ключ-значение для безопасного отображения
    
    Args:
        key: Ключ
        value: Значение
        bullet: Маркер списка
        
    Returns:
        Отформатированная строка
    """
    safe_key = escape_markdown(str(key))
    safe_value = escape_markdown(str(value))
    return f"{bullet} *{safe_key}*: `{safe_value}`" 