from pysnmp.hlapi import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
import subprocess
import asyncio

def get_snmp_info(ip, community='public', timeout=2, port=161):
    oids = {
        'sysName': '1.3.6.1.2.1.1.5.0',
        'sysUpTime': '1.3.6.1.2.1.1.3.0',
        'sysDescr': '1.3.6.1.2.1.1.1.0',
    }
    result = {}
    for key, oid in oids.items():
        try:
            errorIndication, errorStatus, errorIndex, varBinds = next(
                getCmd(SnmpEngine(),
                       CommunityData(community, mpModel=1),
                       UdpTransportTarget((ip, port), timeout=timeout, retries=1),
                       ContextData(),
                       ObjectType(ObjectIdentity(oid)))
            )
            print(f"DEBUG {ip} {key}: errorIndication={errorIndication}, errorStatus={errorStatus}, varBinds={varBinds}")
            if errorIndication:
                result[key] = f"SNMP error: {errorIndication}"
            elif errorStatus:
                result[key] = f"SNMP error: {errorStatus.prettyPrint()}"
            else:
                for varBind in varBinds:
                    result[key] = str(varBind[1])
        except Exception as e:
            result[key] = f"Exception: {e}"
    return result

def get_snmp_info_subprocess(ip, community='public'):
    oids = {
        'sysName': '1.3.6.1.2.1.1.5.0',
        'sysUpTime': '1.3.6.1.2.1.1.3.0',
        'sysDescr': '1.3.6.1.2.1.1.1.0',
    }
    result = {}
    for key, oid in oids.items():
        try:
            out = subprocess.check_output(
                ['snmpget', '-v', '2c', '-c', community, '-Oqv', ip, oid],
                stderr=subprocess.STDOUT,
                timeout=3
            )
            result[key] = out.decode().strip()
        except Exception as e:
            result[key] = f"Exception: {e}"
    return result

async def async_get_snmp_info_subprocess(ip, community='public', timeout=3):
    oids = {
        'sysName': '1.3.6.1.2.1.1.5.0',
        'sysUpTime': '1.3.6.1.2.1.1.3.0',
        'sysDescr': '1.3.6.1.2.1.1.1.0',
    }
    result = {}
    for key, oid in oids.items():
        try:
            proc = await asyncio.create_subprocess_exec(
                'snmpget', '-v', '2c', '-c', community, '-Oqv', ip, oid,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            try:
                out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                result[key] = '⏳ Таймаут'
                continue
            if proc.returncode == 0:
                value = out.decode().strip()
                result[key] = value
            else:
                err_str = err.decode().strip()
                if 'Timeout' in err_str or 'timed out' in err_str:
                    result[key] = '⏳ Таймаут'
                else:
                    result[key] = '⛔ Нет ответа'
        except Exception:
            result[key] = '⛔ Нет ответа'
    return result

def parse_if_table(output):
    # Парсит snmpwalk -Oqv вывод для ifDescr, ifOperStatus, ifInOctets, ifOutOctets
    return [line.strip() for line in output.decode().splitlines() if line.strip()]

async def async_get_snmp_full_info(ip, community='public', timeout=3):
    # Основные OID
    oids = {
        'sysName': '1.3.6.1.2.1.1.5.0',
        'sysDescr': '1.3.6.1.2.1.1.1.0',
        'sysUpTime': '1.3.6.1.2.1.1.3.0',
        'sysContact': '1.3.6.1.2.1.1.4.0',
        'sysLocation': '1.3.6.1.2.1.1.6.0',
        'ifNumber': '1.3.6.1.2.1.2.1.0',
    }
    result = {}
    # Опрос основных OID
    for key, oid in oids.items():
        try:
            proc = await asyncio.create_subprocess_exec(
                'snmpget', '-v', '2c', '-c', community, '-Oqv', ip, oid,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            try:
                out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                result[key] = '⏳ Таймаут'
                continue
            if proc.returncode == 0:
                value = out.decode().strip()
                result[key] = value
            else:
                err_str = err.decode().strip()
                if 'Timeout' in err_str or 'timed out' in err_str:
                    result[key] = '⏳ Таймаут'
                else:
                    result[key] = '⛔ Нет ответа'
        except Exception:
            result[key] = '⛔ Нет ответа'
    # Опрос таблиц интерфейсов (walk)
    if_descr, if_status, if_in, if_out = [], [], [], []
    try:
        proc = await asyncio.create_subprocess_exec(
            'snmpwalk', '-v', '2c', '-c', community, '-Oqv', ip, '1.3.6.1.2.1.2.2.1.2',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if_descr = parse_if_table(out)
    except Exception:
        if_descr = []
    try:
        proc = await asyncio.create_subprocess_exec(
            'snmpwalk', '-v', '2c', '-c', community, '-Oqv', ip, '1.3.6.1.2.1.2.2.1.8',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if_status = parse_if_table(out)
    except Exception:
        if_status = []
    try:
        proc = await asyncio.create_subprocess_exec(
            'snmpwalk', '-v', '2c', '-c', community, '-Oqv', ip, '1.3.6.1.2.1.2.2.1.10',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if_in = parse_if_table(out)
    except Exception:
        if_in = []
    try:
        proc = await asyncio.create_subprocess_exec(
            'snmpwalk', '-v', '2c', '-c', community, '-Oqv', ip, '1.3.6.1.2.1.2.2.1.16',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if_out = parse_if_table(out)
    except Exception:
        if_out = []
    # Собираем интерфейсы
    interfaces = []
    n = max(len(if_descr), len(if_status), len(if_in), len(if_out))
    for i in range(n):
        interfaces.append({
            'descr': if_descr[i] if i < len(if_descr) else '-',
            'status': if_status[i] if i < len(if_status) else '-',
            'in_octets': if_in[i] if i < len(if_in) else '-',
            'out_octets': if_out[i] if i < len(if_out) else '-',
        })
    result['interfaces'] = interfaces
    return result 