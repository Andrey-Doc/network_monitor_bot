import asyncio
import ipaddress
import socket
from typing import List, Dict, Optional
from telegram_bot.utils.settings_manager import SettingsManager
import os

settings_manager = SettingsManager(base_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data')))
# Используйте settings_manager.get_setting('...') для получения нужных параметров.

# Порты для быстрой проверки (можно расширить)
FAST_PORTS = [80, 8080, 22, 161, 443, 554, 4028, 62078, 5555]

PORT_TO_TYPE = {
    80: 'web',
    8080: 'web',
    22: 'ssh',
    161: 'switch',
    443: 'web',
    554: 'camera',
    4028: 'miner',
    62078: 'phone',
    5555: 'phone',
}

async def check_port(ip: str, port: int, timeout: float = 0.5) -> bool:
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

async def fast_scan_device(ip: str) -> Optional[Dict]:
    open_ports = []
    types = set()
    for port in FAST_PORTS:
        if await check_port(ip, port):
            open_ports.append(port)
            t = PORT_TO_TYPE.get(port)
            if t:
                types.add(t)
    if open_ports:
        return {
            'ip': ip,
            'open_ports': open_ports,
            'type': ', '.join(types) if types else 'unknown',
        }
    return None

async def fast_scan_network(network: str, on_progress=None, max_concurrent: int = 50) -> List[Dict]:
    net = ipaddress.IPv4Network(network, strict=False)
    hosts = [str(ip) for ip in net.hosts()]
    results = []
    total = len(hosts)
    sem = asyncio.Semaphore(max_concurrent)
    progress = {'done': 0}

    async def scan_and_report(ip):
        async with sem:
            res = await fast_scan_device(ip)
            progress['done'] += 1
            if on_progress and (progress['done'] % max(1, total // 20) == 0 or progress['done'] == total):
                await on_progress(progress['done'], total)
            return res

    tasks = [scan_and_report(ip) for ip in hosts]
    scan_results = await asyncio.gather(*tasks)
    for res in scan_results:
        if res:
            results.append(res)
    return results 