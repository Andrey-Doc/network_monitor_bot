import asyncio
import logging
from typing import Dict, List
from telegram_bot.utils.router_monitor import check_routers_status
from telegram_bot.utils.settings_manager import SettingsManager
from telegram_bot.bot.translations import translate
import os

settings_manager = SettingsManager(base_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data')))

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
        initial_status = await check_routers_status(
            settings_manager.get_setting('routers.ips', []),
            settings_manager.get_setting('routers.ports', [8080, 80, 22])
        )
        offline_routers = []
        for router in initial_status:
            self.previous_status[router['ip']] = router['status']
            if router['status'] != 'online':
                offline_routers.append({
                    'ip': router['ip'],
                    'old_status': None,
                    'new_status': router['status'],
                    'open_ports': router.get('open_ports', [])
                })
        # Если есть offline-роутеры при первом запуске — отправить уведомление
        if offline_routers:
            await self._send_status_notification(offline_routers)
        
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
                current_status = await check_routers_status(
                    settings_manager.get_setting('routers.ips', []),
                    settings_manager.get_setting('routers.ports', [8080, 80, 22])
                )
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
        # Получаем язык (можно доработать под пользователя)
        lang = 'ru'  # или получить из настроек
        message = str(translate(lang, 'router_status_change_title') or '') + "\n\n"
        for change in changes:
            emoji = "🟢" if change['new_status'] == 'online' else "🔴"
            old_status = change['old_status'] if change['old_status'] is not None else 'unknown'
            new_status = change['new_status'] if change['new_status'] is not None else 'unknown'
            open_ports = change['open_ports'] if change.get('open_ports') is not None else []
            message += str(translate(lang, 'router_status_change_line', emoji=emoji, ip=change['ip'], old_status=old_status, new_status=new_status) or '') + "\n"
            if new_status == 'online' and open_ports:
                message += str(translate(lang, 'router_status_change_ports', ports=', '.join(map(str, open_ports))) or '') + "\n"
            message += "\n"
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logging.info(f"[MONITOR] Отправлено уведомление об изменении статуса {len(changes)} роутеров")
        except Exception as e:
            logging.error(f"[MONITOR] Ошибка отправки уведомления: {e}")
            
    async def get_current_status(self) -> Dict:
        """Возвращает текущий статус всех роутеров"""
        return self.previous_status.copy() 