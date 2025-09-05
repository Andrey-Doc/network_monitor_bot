FROM python:3.8-slim-bullseye

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    nmap \
    snmp \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание директорий для данных
RUN mkdir -p data/scan_results

# Установка Python пути
ENV PYTHONPATH=/app

# Запуск бота (ИСПРАВЛЕННАЯ КОМАНДА)
CMD python3 -m telegram_bot.bot.main
