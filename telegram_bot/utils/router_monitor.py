import asyncio
import socket
from typing import List, Dict

ROUTER_PORTS = [8080, 8022]

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

async def check_router_status(ip: str) -> Dict:
    status = False
    open_ports = []
    for port in ROUTER_PORTS:
        if await check_port(ip, port):
            status = True
            open_ports.append(port)
    return {
        'ip': ip,
        'status': 'online' if status else 'offline',
        'open_ports': open_ports
    }

async def check_routers_status(ips: List[str]) -> List[Dict]:
    tasks = [check_router_status(ip) for ip in ips]
    return await asyncio.gather(*tasks) 