import asyncio
import socket
from typing import List, Dict
from telegram_bot.utils.settings_manager import SettingsManager
import os

settings_manager = SettingsManager(base_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data')))
# Используйте settings_manager.get_setting('...') для получения нужных параметров.

async def check_port(ip: str, port: int, timeout: float = 2.0) -> bool:
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(
            None,
            lambda: _check_port_sync(ip, port, timeout)
        )
    except Exception:
        return False

def _check_port_sync(ip: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False

async def check_router_status(ip: str, router_ports: List[int]) -> Dict:
    status = False
    open_ports = []
    for port in router_ports:
        if await check_port(ip, port):
            status = True
            open_ports.append(port)
    return {
        'ip': ip,
        'status': 'online' if status else 'offline',
        'open_ports': open_ports
    }

async def check_routers_status(ips: List[str], router_ports: List[int]) -> List[Dict]:
    tasks = [check_router_status(ip, router_ports) for ip in ips]
    return await asyncio.gather(*tasks) 