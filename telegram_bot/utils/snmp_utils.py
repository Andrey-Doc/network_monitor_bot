from pysnmp.hlapi import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity

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
                       CommunityData(community, mpModel=0),
                       UdpTransportTarget((ip, port), timeout=timeout, retries=1),
                       ContextData(),
                       ObjectType(ObjectIdentity(oid)))
            )
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