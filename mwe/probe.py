import time
import BAC0
from BAC0.core.io.IOExceptions import UnknownPropertyError

# Config
probe_ip = '192.168.183.2'
ip_whitelist = [
    '192.168.183.1',
    '192.168.183.3'
]
device_delay = 0.005
cycle_delay = 5


bacnet = BAC0.lite(ip=probe_ip)

for ip in ip_whitelist:
    bacnet.discover(limits=(ip,'0 4194303'), global_broadcast=False)
devices = dict()
for dev in bacnet.discoveredDevices:
    devices[dev] = bacnet.read(f'{dev[0]} device {dev[1]} objectList')
try:
    while True:
        print('Cycle began at', time.strftime("%d/%m/%Y %T", time.localtime()), flush=True)
        for device, objects in devices.items():
            print(device, end=': \n')
            for obj in objects:
                print('  ' + obj[0], obj[1], sep=':', end=': ')
                try:
                    print(bacnet.read(f'{device[0]} {obj[0]} {obj[1]} description'), flush=True)
                except UnknownPropertyError:
                    print('property unavailable', flush=True)
            time.sleep(device_delay)
        time.sleep(cycle_delay)
except KeyboardInterrupt:
    pass

bacnet.disconnect()
