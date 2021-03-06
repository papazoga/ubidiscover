import socket
import sys
import struct
import binascii
import select

HwAddr           = 1
Address          = 2
FirmwareVersion  = 3
UpTime           = 10
HostName         = 11
Product          = 12
Essid            = 13
WirelessMode     = 14
SystemId         = 16

def _parse_macaddr(bstr):
    raw = binascii.b2a_hex(bstr)
    return "%s:%s:%s:%s:%s:%s" % (raw[0:2], raw[2:4], raw[4:6], raw[6:8], raw[8:10], raw[10:12])

def _parse_response(msg):
    magic, msg_type, msg_length = struct.unpack("!BBH", msg[0:4])
    msg_body = msg[4:]
    cur_pos = 0

    ret = { 'addresses' : [] }
        
    while cur_pos < msg_length:
        rest = msg_body[cur_pos:]
        tlv_type, tlv_length = struct.unpack("!BH", rest[0:3])
        tlv_value = rest[3:3+tlv_length]
                
        if   tlv_type == HwAddr:
            ret['hwaddr'] = _parse_macaddr(tlv_value)
        elif (tlv_type == Address):
            ret['addresses'].append({
                'hwaddr' : _parse_macaddr(tlv_value[0:6]),
                'ipv4'   : socket.inet_ntop(socket.AF_INET, tlv_value[6:])
            })
        elif tlv_type == FirmwareVersion:
            ret['fwversion'] = tlv_value
        elif tlv_type == UpTime:
            ret['uptime'] = struct.unpack("!L", tlv_value)[0]
        elif tlv_type == HostName:
            ret['hostname'] = tlv_value
        elif tlv_type == Product:
            ret['product'] = tlv_value
        elif tlv_type == Essid:
            ret['essid'] = tlv_value
        elif tlv_type == WirelessMode:
            ret['wmode'] = struct.unpack("B", tlv_value)[0]
        elif tlv_type == SystemId:
            ret['sysid'] = struct.unpack("!H", tlv_value)[0]
        else:
            print("unknown type %d. data: %s" % (tlv_type, binascii.b2a_hex(tlv_value)))
                
        cur_pos += tlv_length + 3

    return ret

class UbiDiscover(object):
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def __del__(self):
        self.sock.close()

    def discover(self, hostname, timeout=2):
        self.sock.connect((hostname, 10001))
        self.sock.send(struct.pack("BBBB", 1, 0, 0, 0))

        r,w,x = select.select([self.sock], [], [], timeout)

        if not r:
            return None

        data = self.sock.recv(4096)
        response = _parse_response(data)

        return response


    def discover_multi(self, hostlist, timeout=2):
        responses = []
        for host in hostlist:
            response = self.discover(host, timeout)
            if response:
                responses.append(response)
        return responses


if __name__ == "__main__":
    import json

    d = UbiDiscover()

    if len(sys.argv) < 2:
        hosts = []
        for line in sys.stdin:
            hosts.append(line.strip())

        resp = d.discover_multi(hosts, .2)
        print(json.dumps(resp))
        
    elif len(sys.argv) == 2:
        resp = d.discover(sys.argv[1])
        print(json.dumps(resp))
    else:
        resp = d.discover(sys.argv[1], float(sys.argv[2]))
        print(json.dumps(resp))
