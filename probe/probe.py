import yaml
import time
import BAC0
from BAC0.core.io.IOExceptions import UnknownPropertyError
from os import scandir
from threading import Thread
import sys

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
log_level = 'info'

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

def verify_mapping(mapping):
    flag = False
    for obj in mapping:
        if obj not in object_names.values():
            print(f'Warning: unknown object {obj}')
            flag = True
        for prop in mapping[obj]:
            if prop not in prop_names.values():
                print(f'Warning: unknown property {prop} of object {obj}')
                flag = True
    return flag

def process_device(device, out):
    dev_name = dev[0] + ':' + str(dev[1])
    objects = bacnet.read(f'{device[0]} device {device[1]} objectList')
    results = dict()
    for obj in objects:
        obj_name = obj[0] + ':' + str(obj[1])
        if obj[0] not in mappings:
            results[obj_name] = ' '.join('Skipping object type', obj[0], '(mapping not implemented)')
            continue
        mapping = mappings[obj[0]]
        try:
            vals = bacnet.readMultiple(f'{device[0]} {obj[0]} {obj[1]} {" ".join(mapping.keys())}')
            values = dict(zip(mapping.keys(), vals))
        except: # TODO: find exception for "readMultiple not supported"
            values = dict()
            for key in mapping:
                try:
                    values[key] = bacnet.read(f'{device[0]} {obj[0]} {obj[1]} {key}')
                except UnknownPropertyError:
                    values[key] = None
                time.sleep(property_delay)
        results[obj_name] = values
    out[dev_name] = results

mappings = dict()
for file in scandir('../mappings'):
    if not file.name.endswith('.yaml'):
        continue
    with open(file, 'r') as fin:
        obj = yaml.safe_load(fin)
        mappings.update(update_names(obj))

if verify_mapping(mappings):
    sys.exit()

BAC0.log_level(stdout=log_level)
bacnet = BAC0.lite(ip=probe_ip)

for ip in ip_whitelist:
    bacnet.discover(limits=(ip, ''), global_broadcast=False)

data = dict()

for dev in bacnet.discoveredDevices:
    process_device(dev, data)
    time.sleep(device_delay)
with open(output_filename, 'a') as fout:
    print(time.strftime('%Y/%m/%d %H:%M:%S', time.localtime()), file=fout)
    if len(data) == 0:
        print('Failed to discover devices', file=fout)
    else:
        for dev in data:
            print(dev, file=fout)
            dev_data = data[dev]
            for obj_name in dev_data:
                print('  ' + obj_name, file=fout)
                obj_data = dev_data[obj_name]
                for prop_name in obj_data:
                    print('    ' + prop_name, end=': ', file=fout)
                    if obj_data[prop_name] is None:
                        print('property unavailable', file=fout)
                    else:
                        print(obj_data[prop_name], file=fout)

bacnet.disconnect()
