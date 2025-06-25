from pysnmp.hlapi.sync.cmdgen import getCmd, SnmpEngine, CommunityData, UdpTransportTarget, ContextData, ObjectType, ObjectIdentity

def get_snmp_info(ip, community='public', timeout=2, port=161):
    oids = {
        'sysName': '1.3.6.1.2.1.1.5.0',
        'sysUpTime': '1.3.6.1.2.1.1.3.0',
        'sysDescr': '1.3.6.1.2.1.1.1.0',
    }
    result = {}
    for key, oid in oids.items():
        errorIndication, errorStatus, errorIndex, varBinds = next(
            getCmd(SnmpEngine(),
                   CommunityData(community, mpModel=0),
                   UdpTransportTarget((ip, port), timeout=timeout, retries=1),
                   ContextData(),
                   ObjectType(ObjectIdentity(oid)))
        )
        if errorIndication or errorStatus:
            result[key] = None
        else:
            for varBind in varBinds:
                result[key] = str(varBind[1])
    return result 