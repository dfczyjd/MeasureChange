import time

import BAC0
from BAC0.core.io.IOExceptions import UnknownObjectError, UnknownPropertyError

bacnet = BAC0.connect(ip='192.168.183.2')

res = bacnet.discover(networks='known', limits=(0,4194303), global_broadcast=False)
print('Discovered devices:')
for dev in bacnet.discoveredDevices:
    print(' ', dev)
while True:
    cmd = input()
    if cmd == 'exit':
        break
    obj, obj_id, attr = cmd.split()
    for device in bacnet.discoveredDevices:
        print(device, end=': ')
        try:
            print(bacnet.read(f'{device[0]} {obj} {obj_id} {attr}'), flush=True)
        except UnknownObjectError as err:
            print(f'Unknown object ({err})')
        except UnknownPropertyError as err:
            print(f'Unknown property ({err})')
        except Exception as err:
            print(f'Unknown error {err}')
        time.sleep(0.005)

print('Entering shell mode', flush=True)

while True:
    cmd = input()
    if cmd == 'exit':
        break
    print(eval(cmd))

bacnet.disconnect()
"""
obj = test_device.points[0]
for prop in obj.bacnet_properties:
    print(prop + ':', obj.bacnet_properties[prop])
print()
print(*test_device.points, sep='\n', end='\n\n')
print(*test_device_30.points, sep='\n')
"""