import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import os

class StatisticsManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.stats_file = os.path.join(data_dir, "statistics.json")
        self.daily_stats_file = os.path.join(data_dir, "daily_stats.json")
        self.ensure_data_dir()
        self.load_statistics()
        
    def ensure_data_dir(self):
        """Создаёт директорию для данных если её нет"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
    def load_statistics(self):
        """Загружает статистику из файла"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
            else:
                self.stats = self._get_default_stats()
                
            if os.path.exists(self.daily_stats_file):
                with open(self.daily_stats_file, 'r', encoding='utf-8') as f:
                    self.daily_stats = json.load(f)
            else:
                self.daily_stats = {}
                
        except Exception as e:
            logging.error(f"[STATS] Ошибка загрузки статистики: {e}")
            self.stats = self._get_default_stats()
            self.daily_stats = {}
            
    def save_statistics(self):
        """Сохраняет статистику в файл"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
                
            with open(self.daily_stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.daily_stats, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logging.error(f"[STATS] Ошибка сохранения статистики: {e}")
            
    def _get_default_stats(self) -> Dict:
        """Возвращает структуру статистики по умолчанию"""
        return {
            'total_commands': 0,
            'total_scans': 0,
            'total_devices_found': 0,
            'total_miners_found': 0,
            'total_router_checks': 0,
            'total_errors': 0,
            'start_time': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'commands_by_type': {
                'status_routers': 0,
                'scan_network': 0,
                'scan_miners': 0,
                'fast_scan': 0,
                'upload_file': 0
            },
            'scan_results': {
                'networks_scanned': 0,
                'total_ips_scanned': 0,
                'devices_by_type': {
                    'miners': 0,
                    'routers': 0,
                    'other': 0
                }
            },
            'monitoring': {
                'total_checks': 0,
                'status_changes': 0,
                'uptime_percentage': 100.0
            }
        }
        
    def record_command(self, command_type: str):
        """Записывает выполнение команды"""
        self.stats['total_commands'] += 1
        self.stats['last_activity'] = datetime.now().isoformat()
        
        if command_type in self.stats['commands_by_type']:
            self.stats['commands_by_type'][command_type] += 1
            
        self._record_daily_stat('commands', command_type)
        self.save_statistics()
        
    def record_scan(self, scan_type: str, devices_found: int, ips_scanned: int, duration: float):
        """Записывает результаты сканирования"""
        self.stats['total_scans'] += 1
        self.stats['total_devices_found'] += devices_found
        self.stats['scan_results']['networks_scanned'] += 1
        self.stats['scan_results']['total_ips_scanned'] += ips_scanned
        
        # Определяем тип устройств
        if scan_type == 'miners':
            self.stats['total_miners_found'] += devices_found
            self.stats['scan_results']['devices_by_type']['miners'] += devices_found
        elif scan_type == 'routers':
            self.stats['scan_results']['devices_by_type']['routers'] += devices_found
        else:
            self.stats['scan_results']['devices_by_type']['other'] += devices_found
            
        self._record_daily_stat('scans', {
            'type': scan_type,
            'devices_found': devices_found,
            'ips_scanned': ips_scanned,
            'duration': duration
        })
        self.save_statistics()
        
    def record_router_check(self, routers_online: int, total_routers: int):
        """Записывает проверку роутеров"""
        self.stats['total_router_checks'] += 1
        self.stats['monitoring']['total_checks'] += 1
        
        if total_routers == 0:
            uptime_percentage = 0
        else:
            uptime_percentage = (routers_online / total_routers) * 100
        self.stats['monitoring']['uptime_percentage'] = uptime_percentage
        
        self._record_daily_stat('router_checks', {
            'online': routers_online,
            'total': total_routers,
            'uptime': uptime_percentage
        })
        self.save_statistics()
        
    def record_status_change(self, router_ip: str, old_status: str, new_status: str):
        """Записывает изменение статуса роутера"""
        self.stats['monitoring']['status_changes'] += 1
        
        self._record_daily_stat('status_changes', {
            'router_ip': router_ip,
            'old_status': old_status,
            'new_status': new_status
        })
        self.save_statistics()
        
    def record_error(self, error_type: str, error_message: str):
        """Записывает ошибку"""
        self.stats['total_errors'] += 1
        
        self._record_daily_stat('errors', {
            'type': error_type,
            'message': error_message
        })
        self.save_statistics()
        
    def _record_daily_stat(self, stat_type: str, data):
        """Записывает статистику за день"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if today not in self.daily_stats:
            self.daily_stats[today] = {
                'commands': 0,
                'scans': [],
                'router_checks': [],
                'status_changes': [],
                'errors': []
            }
            
        if stat_type == 'commands':
            self.daily_stats[today]['commands'] += 1
        else:
            self.daily_stats[today][stat_type].append({
                'timestamp': datetime.now().isoformat(),
                'data': data
            })
            
    def get_summary_stats(self) -> Dict:
        """Возвращает сводную статистику"""
        uptime = self.stats['monitoring']['uptime_percentage']
        total_time = datetime.now() - datetime.fromisoformat(self.stats['start_time'])
        
        return {
            'uptime_percentage': uptime,
            'total_commands': self.stats['total_commands'],
            'total_scans': self.stats['total_scans'],
            'total_devices_found': self.stats['total_devices_found'],
            'total_miners_found': self.stats['total_miners_found'],
            'total_router_checks': self.stats['total_router_checks'],
            'total_errors': self.stats['total_errors'],
            'bot_uptime_days': total_time.days,
            'last_activity': self.stats['last_activity']
        }
        
    def get_daily_stats(self, days: int = 7) -> List[Dict]:
        """Возвращает статистику за последние дни"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        daily_data = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            day_stats = self.daily_stats.get(date_str, {})
            
            daily_data.append({
                'date': date_str,
                'commands': day_stats.get('commands', 0),
                'scans': len(day_stats.get('scans', [])),
                'router_checks': len(day_stats.get('router_checks', [])),
                'status_changes': len(day_stats.get('status_changes', [])),
                'errors': len(day_stats.get('errors', []))
            })
            
            current_date += timedelta(days=1)
            
        return daily_data
        
    def generate_report(self) -> str:
        """Генерирует текстовый отчёт"""
        summary = self.get_summary_stats()
        daily_stats = self.get_daily_stats(7)
        
        report = "📊 *Отчёт статистики бота*\n\n"
        
        # Общая статистика
        report += "🔢 *Общая статистика:*\n"
        report += f"• Команд выполнено: `{summary['total_commands']}`\n"
        report += f"• Сканирований: `{summary['total_scans']}`\n"
        report += f"• Устройств найдено: `{summary['total_devices_found']}`\n"
        report += f"• Майнеров найдено: `{summary['total_miners_found']}`\n"
        report += f"• Проверок роутеров: `{summary['total_router_checks']}`\n"
        report += f"• Ошибок: `{summary['total_errors']}`\n"
        report += f"• Время работы: `{summary['bot_uptime_days']}` дней\n\n"
        
        # Мониторинг
        report += "🌐 *Мониторинг роутеров:*\n"
        report += f"• Доступность: `{summary['uptime_percentage']:.1f}%`\n"
        report += f"• Изменений статуса: `{self.stats['monitoring']['status_changes']}`\n\n"
        
        # Статистика по командам
        report += "📋 *Популярные команды:*\n"
        for cmd, count in sorted(
            self.stats['commands_by_type'].items(), 
            key=lambda x: x[1], 
            reverse=True
        ):
            if count > 0:
                # Экранируем специальные символы в названиях команд
                safe_cmd = cmd.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`')
                report += f"• `{safe_cmd}`: `{count}`\n"
        report += "\n"
        
        # Статистика за неделю
        report += "📈 *Активность за неделю:*\n"
        for day in daily_stats[-7:]:
            report += f"• `{day['date']}`: `{day['commands']}` команд, `{day['scans']}` сканирований\n"
            
        return report
        
    def export_csv(self) -> str:
        """Экспортирует статистику в CSV"""
        csv_content = "Дата,Команды,Сканирования,Проверки роутеров,Изменения статуса,Ошибки\n"
        
        daily_stats = self.get_daily_stats(30)  # За месяц
        
        for day in daily_stats:
            csv_content += f"{day['date']},{day['commands']},{day['scans']},{day['router_checks']},{day['status_changes']},{day['errors']}\n"
            
        return csv_content 