import time
import BAC0
from BAC0.core.io.IOExceptions import UnknownPropertyError


bacnet = BAC0.connect(ip='192.168.183.2')

res = bacnet.discover(networks='known', limits=(0,4194303), global_broadcast=False)
devices = dict()
for dev in bacnet.discoveredDevices:
    devices[dev] = bacnet.read(f'{dev[0]} device {dev[1]} objectList')
print(devices)
while True:
    print('Cycle begin', flush=True)
    for device, objects in devices.items():
        for obj in objects:
            print(obj[0], obj[1], sep=':', end=': ')
            try:
                print(bacnet.read(f'{device[0]} {obj[0]} {obj[1]} presentValue'), flush=True)
            except UnknownPropertyError:
                print('property unavailable', flush=True)
        time.sleep(0.005)
    time.sleep(1)

bacnet.disconnect()
