import asyncio
import socket
import ipaddress
from typing import List, Dict, Optional
import logging
from .miner_scan import get_miner_info
import time
from telegram_bot.utils.settings_manager import SettingsManager
import os

settings_manager = SettingsManager(base_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data')))
# Используйте settings_manager.get_setting('...') для получения нужных параметров.

# Порты для определения типа устройства
DEVICE_PORTS = {
    'router': [80, 8080, 443, 23, 22],
    'switch': [161, 23, 22],
    'miner': [4028],
    'camera': [554, 80, 8080],
    'phone': [62078, 5555],
}

PORT_TO_TYPE = {}
for dtype, ports in DEVICE_PORTS.items():
    for port in ports:
        PORT_TO_TYPE.setdefault(port, []).append(dtype)

COMMON_PORTS = list(set([p for ports in DEVICE_PORTS.values() for p in ports]))

async def check_port(ip: str, port: int, timeout: float = 1.5) -> bool:
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

async def scan_device(ip: str) -> Optional[Dict]:
    open_ports = []
    is_miner = False
    hashrate = None
    uptime = None
    for port in COMMON_PORTS:
        if await check_port(ip, port):
            open_ports.append(port)
            if port == 4028:
                is_miner = True
    result = {
        'ip': ip,
        'open_ports': open_ports,
        'type': '',
    }
    if is_miner:
        result['type'] = 'miner'
        miner_info = await get_miner_info(ip)
        if miner_info:
            result['hashrate'] = miner_info.get('hashrate')
            result['uptime'] = miner_info.get('uptime')
        else:
            result['hashrate'] = None
            result['uptime'] = None
    return result if open_ports else None

async def scan_network_devices(network: str, on_progress=None) -> List[Dict]:
    net = ipaddress.IPv4Network(network, strict=False)
    hosts = [str(ip) for ip in net.hosts()]
    logging.info(f"[SCAN] Всего хостов для сканирования: {len(hosts)}")
    results = []
    total = len(hosts)
    start_time = time.time()
    for idx, ip in enumerate(hosts, 1):
        logging.info(f"[SCAN] Сканирую {ip} ({idx}/{total}) - найдено устройств: {len(results)}")
        res = await scan_device(ip)
        if res:
            results.append(res)
            logging.info(f"[SCAN] Найдено устройство: {ip} - {res.get('type', 'unknown')}")
        if on_progress and (idx % max(1, total // 20) == 0 or idx == total):
            elapsed = time.time() - start_time
            logging.info(f"[SCAN] Вызов on_progress: {idx}/{total} - время: {elapsed:.1f}с")
            await on_progress(idx, total)
        await asyncio.sleep(0)
    total_time = time.time() - start_time
    logging.info(f"[SCAN] Сканирование завершено за {total_time:.1f}с, найдено: {len(results)}")
    return results 