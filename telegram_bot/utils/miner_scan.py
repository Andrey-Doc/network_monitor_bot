import asyncio
import socket
import json
import logging
from typing import List, Dict, Optional
import ipaddress
import os
from telegram_bot.utils.settings_manager import SettingsManager

MINER_PORT = 4028
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

async def get_miner_info(ip: str, port: int = MINER_PORT, timeout: float = 3.0) -> Optional[Dict]:
    # Пробуем получить информацию через API майнера (Antminer, Avalon, Whatsminer)
    # Обычно это TCP socket, команда: {"command": "summary"}
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=timeout)
        writer.write(b'{"command": "summary"}\n')
        await writer.drain()
        data = await asyncio.wait_for(reader.read(4096), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        # Попытка декодировать ответ
        try:
            text = data.decode(errors='ignore')
            # Иногда ответ невалидный JSON, пробуем найти {...}
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                text = text[start:end+1]
            info = json.loads(text)
            # Универсальный парсинг для разных моделей
            hashrate = None
            uptime = None
            status = 'online'
            if 'SUMMARY' in info:
                s = info['SUMMARY'][0]
                hashrate = s.get('MHS av') or s.get('GHS av') or s.get('hashrate')
                uptime = s.get('Elapsed') or s.get('Uptime')
            return {
                'ip': ip,
                'status': status,
                'hashrate': hashrate,
                'uptime': uptime
            }
        except Exception:
            return {'ip': ip, 'status': 'online', 'hashrate': None, 'uptime': None}
    except Exception:
        return None

async def scan_network_for_miners(network: str, on_progress=None) -> List[Dict]:
    net = ipaddress.IPv4Network(network, strict=False)
    hosts = [str(ip) for ip in net.hosts()]
    results = []
    total = len(hosts)
    for idx, ip in enumerate(hosts, 1):
        logging.info(f"[SCAN_MINERS] Проверяю {ip} ({idx}/{total})")
        res = await scan_miner(ip)
        if res:
            logging.info(f"[SCAN_MINERS] Найден майнер: {ip}")
            results.append(res)
        if on_progress and (idx % max(1, total // 20) == 0 or idx == total):
            await on_progress(idx, total)
        await asyncio.sleep(0)
    return results

async def scan_miner(ip: str, port: int = 4028, timeout: float = 1.5) -> Optional[Dict]:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=timeout)
        writer.write(b'{"command": "summary"}\n')
        await writer.drain()
        data = await asyncio.wait_for(reader.read(4096), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        text = data.decode(errors='ignore')
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end+1]
        info = json.loads(text)
        hashrate = None
        uptime = None
        if 'SUMMARY' in info:
            s = info['SUMMARY'][0]
            hashrate = s.get('MHS av') or s.get('GHS av') or s.get('hashrate')
            uptime = s.get('Elapsed')
        return {
            'ip': ip,
            'hashrate': hashrate,
            'uptime': uptime,
            'type': 'miner',
        }
    except Exception as e:
        logging.debug(f"[SCAN_MINERS] {ip}: не майнер или не отвечает ({e})")
        return None

async def scan_miners_from_list(ip_list: List[str]) -> List[Dict]:
    tasks = [scan_miner(ip) for ip in ip_list]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r]

async def get_asic_status(ip, port=4028, timeout=3):
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=timeout)
        writer.write(b'{"command": "summary"}\n')
        await writer.drain()
        data = await asyncio.wait_for(reader.read(4096), timeout=timeout)
        writer.close()
        await writer.wait_closed()
        text = data.decode(errors='ignore')
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end+1]
        info = json.loads(text)
        hashrate = None
        uptime = None
        if 'SUMMARY' in info:
            s = info['SUMMARY'][0]
            hashrate = s.get('MHS av') or s.get('GHS av') or s.get('hashrate')
            uptime = s.get('Elapsed') or s.get('Uptime')
        return {
            'ip': ip,
            'status': 'online',
            'hashrate': hashrate,
            'uptime': uptime,
            'is_hashing': hashrate and float(hashrate) > 0
        }
    except Exception:
        return {'ip': ip, 'status': 'offline', 'hashrate': None, 'uptime': None, 'is_hashing': False} 