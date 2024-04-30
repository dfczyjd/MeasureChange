import yaml
import time
import BAC0
from BAC0.core.io.IOExceptions import UnknownPropertyError
from os import scandir

from bacpypes.basetypes import PropertyIdentifier, ObjectTypesSupported

# Config

probe_ip = '192.168.183.2'
ip_whitelist = [
    '192.168.183.1',
    '192.168.183.3'
]
property_delay = 0.0005
device_delay = 0.005
output_filename = 'data.txt'
log_level = 'debug'

# TODO: find how BAC0 name stuff and fix in mappings
object_names = dict([(x.lower(), x) for x in ObjectTypesSupported().bitNames.keys()])
prop_names = dict([(x.lower(), x) for x in PropertyIdentifier().enumerations.keys()])

def convert_mapping_name(name):
    name_lower = ''.join(name.split()).lower()
    if name_lower in object_names:
        return object_names[name_lower]
    if name_lower in prop_names:
        return prop_names[name_lower]
    return name

def update_names(obj):
    if type(obj) is list:
        res_list = []
        for elem in obj:
            res_list.append(update_names(elem))
        if type(res_list[0]) is dict:
            res = dict()
            for elem in res_list:
                res.update(elem)
            return res
        return res_list
    if type(obj) is dict:
        res = dict()
        for key in obj:
            res[convert_mapping_name(key)] = update_names(obj[key])
        return res
    return obj

mappings = dict()
for file in scandir('../mappings'):
    if not file.name.endswith('.yaml'):
        continue
    with open(file, 'r') as fin:
        obj = yaml.safe_load(fin)
        mappings.update(update_names(obj))
        
BAC0.log_level(log_level)
bacnet = BAC0.lite(ip=probe_ip)

for ip in ip_whitelist:
    bacnet.discover(limits=(ip, ''), global_broadcast=False)
devices = dict()
print('Found', bacnet.discoveredDevices)
for dev in bacnet.discoveredDevices:
    objects = bacnet.read(f'{dev[0]} device {dev[1]} objectList')
    print('Objects on device:', objects)
    devices[dev] = objects
print('Devices:', devices)
if len(devices) == 0:
    print('Fail')
with open(output_filename, 'a') as fout:
    print(time.strftime('%Y/%M/%d %H:%M:%S', time.localtime()), file=fout)
    for device, objects in devices.items():
        print(device, end=': \n')
        for obj in objects:
            if obj[0] not in mappings:
                print('Skipping object type', obj[0], '(mapping not implemented)', file=fout)
                continue
            print(obj[0], obj[1], sep=':', end=':\n', file=fout)
            mapping = mappings[obj[0]]
            for key in mapping:
                print('  ' + key, end=': ', file=fout)
                try:
                    print(bacnet.read(f'{device[0]} {obj[0]} {obj[1]} {key}'), file=fout)
                except UnknownPropertyError:
                    print('property unavailable', file=fout)
                time.sleep(property_delay)
        time.sleep(device_delay)

bacnet.disconnect()
