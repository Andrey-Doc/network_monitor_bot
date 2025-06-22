import asyncio
import logging
from typing import Dict, List
from telegram_bot.utils.router_monitor import check_routers_status
from telegram_bot.bot.config import ROUTER_IPS, ROUTER_PORTS

class BackgroundMonitor:
    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id
        self.previous_status = {}
        self.is_running = False
        self.monitoring_task = None
        
    async def start_monitoring(self, interval: int = 300):  # 5 минут по умолчанию
        """Запускает фоновый мониторинг"""
        if self.is_running:
            logging.warning("[MONITOR] Мониторинг уже запущен")
            return
            
        self.is_running = True
        logging.info(f"[MONITOR] Запуск фонового мониторинга с интервалом {interval}с")
        
        # Инициализация начального статуса
        initial_status = await check_routers_status(ROUTER_IPS, ROUTER_PORTS)
        for router in initial_status:
            self.previous_status[router['ip']] = router['status']
        
        self.monitoring_task = asyncio.create_task(self._monitoring_loop(interval))
        
    async def stop_monitoring(self):
        """Останавливает фоновый мониторинг"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logging.info("[MONITOR] Фоновый мониторинг остановлен")
        
    async def _monitoring_loop(self, interval: int):
        """Основной цикл мониторинга"""
        while self.is_running:
            try:
                current_status = await check_routers_status(ROUTER_IPS, ROUTER_PORTS)
                await self._check_status_changes(current_status)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"[MONITOR] Ошибка в цикле мониторинга: {e}")
                await asyncio.sleep(60)  # Пауза при ошибке
                
    async def _check_status_changes(self, current_status: List[Dict]):
        """Проверяет изменения статуса и отправляет уведомления"""
        changes = []
        
        for router in current_status:
            ip = router['ip']
            current_state = router['status']
            previous_state = self.previous_status.get(ip)
            
            if previous_state != current_state:
                changes.append({
                    'ip': ip,
                    'old_status': previous_state,
                    'new_status': current_state,
                    'open_ports': router['open_ports']
                })
                self.previous_status[ip] = current_state
        
        if changes:
            await self._send_status_notification(changes)
            
    async def _send_status_notification(self, changes: List[Dict]):
        """Отправляет уведомление об изменении статуса"""
        message = "🔄 **Изменение статуса роутеров:**\n\n"
        
        for change in changes:
            emoji = "🟢" if change['new_status'] == 'online' else "🔴"
            message += f"{emoji} **{change['ip']}**: "
            message += f"{change['old_status']} → {change['new_status']}\n"
            
            if change['new_status'] == 'online' and change['open_ports']:
                message += f"   📡 Открытые порты: {', '.join(map(str, change['open_ports']))}\n"
            message += "\n"
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logging.info(f"[MONITOR] Отправлено уведомление об изменении статуса {len(changes)} роутеров")
        except Exception as e:
            logging.error(f"[MONITOR] Ошибка отправки уведомления: {e}")
            
    async def get_current_status(self) -> Dict:
        """Возвращает текущий статус всех роутеров"""
        return self.previous_status.copy() 