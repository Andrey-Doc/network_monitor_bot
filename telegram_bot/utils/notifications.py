import asyncio
import logging
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime

class NotificationLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SUCCESS = "success"

class NotificationType(Enum):
    ROUTER_STATUS = "router_status"
    SCAN_COMPLETE = "scan_complete"
    SCAN_ERROR = "scan_error"
    SYSTEM_ALERT = "system_alert"
    DAILY_REPORT = "daily_report"

class NotificationManager:
    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id
        self.notification_queue = asyncio.Queue()
        self.is_running = False
        self.processing_task = None
        
    async def start(self):
        """Запускает обработчик уведомлений"""
        if self.is_running:
            return
            
        self.is_running = True
        self.processing_task = asyncio.create_task(self._process_notifications())
        logging.info("[NOTIFICATIONS] Система уведомлений запущена")
        
    async def stop(self):
        """Останавливает обработчик уведомлений"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        logging.info("[NOTIFICATIONS] Система уведомлений остановлена")
        
    async def send_notification(self, 
                              level: NotificationLevel,
                              notification_type: NotificationType,
                              title: str,
                              message: str,
                              data: Optional[Dict] = None):
        """Отправляет уведомление"""
        notification = {
            'level': level,
            'type': notification_type,
            'title': title,
            'message': message,
            'data': data or {},
            'timestamp': datetime.now()
        }
        
        await self.notification_queue.put(notification)
        
    async def _process_notifications(self):
        """Обрабатывает очередь уведомлений"""
        while self.is_running:
            try:
                notification = await asyncio.wait_for(
                    self.notification_queue.get(), 
                    timeout=1.0
                )
                await self._send_notification(notification)
                self.notification_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logging.error(f"[NOTIFICATIONS] Ошибка обработки уведомления: {e}")
                
    async def _send_notification(self, notification: Dict):
        """Отправляет уведомление в Telegram"""
        level = notification['level']
        notification_type = notification['type']
        title = notification['title']
        message = notification['message']
        timestamp = notification['timestamp'].strftime("%H:%M:%S")
        
        # Эмодзи для уровней
        level_emoji = {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️", 
            NotificationLevel.CRITICAL: "🚨",
            NotificationLevel.SUCCESS: "✅"
        }
        
        # Эмодзи для типов
        type_emoji = {
            NotificationType.ROUTER_STATUS: "🌐",
            NotificationType.SCAN_COMPLETE: "🔍",
            NotificationType.SCAN_ERROR: "❌",
            NotificationType.SYSTEM_ALERT: "⚙️",
            NotificationType.DAILY_REPORT: "📊"
        }
        
        # Формируем сообщение
        formatted_message = f"{level_emoji[level]} {type_emoji[notification_type]} *{title}*\n"
        formatted_message += f"⏰ {timestamp}\n\n"
        formatted_message += message
        
        # Добавляем данные если есть
        if notification['data']:
            formatted_message += "\n📋 *Детали:*\n"
            for key, value in notification['data'].items():
                formatted_message += f"• {key}: `{value}`\n"
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=formatted_message,
                parse_mode='Markdown'
            )
            logging.info(f"[NOTIFICATIONS] Отправлено уведомление: {title}")
        except Exception as e:
            logging.error(f"[NOTIFICATIONS] Ошибка отправки: {e}")
            
    # Удобные методы для разных типов уведомлений
    async def router_status_change(self, router_ip: str, old_status: str, new_status: str):
        """Уведомление об изменении статуса роутера"""
        level = NotificationLevel.CRITICAL if new_status == 'offline' else NotificationLevel.INFO
        title = f"Изменение статуса роутера {router_ip}"
        message = f"Статус изменился с *{old_status}* на *{new_status}*"
        
        await self.send_notification(
            level=level,
            notification_type=NotificationType.ROUTER_STATUS,
            title=title,
            message=message,
            data={'router_ip': router_ip, 'old_status': old_status, 'new_status': new_status}
        )
        
    async def scan_completed(self, scan_type: str, devices_found: int, duration: float):
        """Уведомление о завершении сканирования"""
        title = f"Сканирование {scan_type} завершено"
        message = f"Найдено устройств: *{devices_found}*\nВремя выполнения: *{duration:.1f}с*"
        
        await self.send_notification(
            level=NotificationLevel.SUCCESS,
            notification_type=NotificationType.SCAN_COMPLETE,
            title=title,
            message=message,
            data={'scan_type': scan_type, 'devices_found': devices_found, 'duration': duration}
        )
        
    async def scan_error(self, scan_type: str, error_message: str):
        """Уведомление об ошибке сканирования"""
        title = f"Ошибка сканирования {scan_type}"
        message = f"Произошла ошибка: *{error_message}*"
        
        await self.send_notification(
            level=NotificationLevel.CRITICAL,
            notification_type=NotificationType.SCAN_ERROR,
            title=title,
            message=message,
            data={'scan_type': scan_type, 'error': error_message}
        )
        
    async def daily_report(self, stats: Dict):
        """Ежедневный отчёт"""
        title = "Ежедневный отчёт мониторинга"
        message = f"""
📊 *Статистика за день:*
• Проверок роутеров: `{stats.get('router_checks', 0)}`
• Сканирований: `{stats.get('scans', 0)}`
• Устройств найдено: `{stats.get('devices_found', 0)}`
• Ошибок: `{stats.get('errors', 0)}`
        """
        
        await self.send_notification(
            level=NotificationLevel.INFO,
            notification_type=NotificationType.DAILY_REPORT,
            title=title,
            message=message,
            data=stats
        ) 