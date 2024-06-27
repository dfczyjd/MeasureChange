import time

import BAC0
from BAC0.core.io.IOExceptions import UnknownObjectError, UnknownPropertyError

import config
import file_reader

bacnet = file_reader.ReadFile(ip=config.probe_ip)
target = '192.168.183.3'

while True:
    print('>>> ', end='', flush=True)
    cmd, args = input().split(' ', 1)
    if cmd == 'exit':
        break
    elif cmd == 'read':
        args = args.split()
        if len(args) < 3:
            print('Usage: read object_type object_id property_names')
            continue
        obj, obj_id, props = args[0], args[1], args[2:]
        try:
            if len(props) == 1:
                print(bacnet.read(f'{target} {obj} {obj_id} {props[0]}'), flush=True)
            else:
                print(bacnet.readMultiple(f'{target} {obj} {obj_id} {" ".join(props)}'), flush=True)
        except UnknownObjectError as err:
            print(f'Unknown object ({err})')
        except UnknownPropertyError as err:
            print(f'Unknown property ({err})')
        except Exception as err:
            print(f'Unknown error {err}')
    elif cmd == 'file':
        args = args.split()
        if len(args) < 2:
            print('Usage: file file_id out_file [chunk_size]')
            continue
        if len(args) == 2:
            file_id, out_file = args
            chunk_size = 1048576 # 1 MB
        else:
            file_id, out_file, chunk_size = args
        file_reader.read_large_file(bacnet, target, int(file_id), out_file, int(chunk_size))
        print('Done', flush=True)
    else:
        print('Unrecognized command:', cmd)

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