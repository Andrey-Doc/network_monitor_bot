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