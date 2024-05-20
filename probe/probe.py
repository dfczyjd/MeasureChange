import yaml
import time
import datetime
import BAC0
from BAC0.core.io.IOExceptions import UnknownPropertyError
from os import scandir
from threading import Thread
import sys
import sqlite3

from bacpypes.basetypes import PropertyIdentifier, ObjectTypesSupported

import config
import patch

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

def process_device(device):
    global data
    dev_name = dev[0]
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
                except e as Exception:
                    values[key] = e
                time.sleep(config.property_delay)
        results[obj_name] = values
    data[dev_name] = results

mappings = dict()
for file in scandir('../mappings'):
    if not file.name.endswith('.yaml'):
        continue
    if file.name == 'Binary Value.yaml':
        continue
    with open(file, 'r') as fin:
        obj = yaml.safe_load(fin)
        mappings.update(update_names(obj))

if verify_mapping(mappings):
    sys.exit()

BAC0.log_level(stdout=config.log_level)
bacnet = BAC0.lite(ip=config.probe_ip)

discovered = []

for ip in config.ip_whitelist:
    try:
        discovered.append((ip, bacnet.read(f'{ip} device {0x3fffff} objectIdentifier')[1]))
    except:
        pass
    time.sleep(config.discovery_delay)

data = dict()

errors = [None] * len(discovered)

timestamp = datetime.datetime.now()
for i, dev in enumerate(discovered):
    try:
        process_device(dev)
        time.sleep(config.device_delay)
    except Exception as e:
        errors[i] = e

try:
    db = sqlite3.connect(config.db_file)
    cur = db.cursor()
    for i, dev in enumerate(data):
        cur.execute('SELECT Id FROM Devices WHERE Address = ?', (dev,))
        row = cur.fetchone()
        if row is None:
            cur.execute('INSERT INTO Devices(Address) VALUES (?)', (dev,))
            dev_id = cur.lastrowid
        else:
            dev_id = row[0]
        if errors[i] is not None:
            cur.execute('INSERT INTO Exceptions(Timestamp, Device, Text) VALUES (?, ?, ?)', (timestamp, dev_id, errors[i]))
        dev_data = data[dev]
        for obj_name in dev_data:
            cur.execute('SELECT Id FROM Objects WHERE Device = ?', (dev_id,))
            row = cur.fetchone()
            if row is None:
                obj_type, bacnet_obj_id = obj_name.split(':')
                cur.execute('INSERT INTO Objects(Device, Type, BACnetId) VALUES (?, ?, ?)', (dev_id, obj_type, bacnet_obj_id))
                obj_id = cur.lastrowid
            else:
                obj_id = row[0]
            obj_data = dev_data[obj_name]
            for prop_name in obj_data:
                value = obj_data[prop_name]
                if value is not None:
                    value = str(value)
                cur.execute('INSERT INTO Properties(Timestamp, Object, Name, Value) VALUES (?, ?, ?, ?)', (timestamp, obj_id, prop_name, value))
    db.commit()
    db.close()
except sqlite3.Error as e:
    print('Exception while writing to the database:')
    print(e)
    sys.exit(0)
    with open(config.output_filename, 'a') as fout:
        print('Exception while writing to the database:', file=fout)
        print(e, file=fout)
        print(time.strftime('%Y/%m/%d %H:%M:%S', timestamp), file=fout)
        if len(data) == 0:
            print('Failed to discover devices', file=fout)
        else:
            for i, dev in enumerate(data):
                print(dev, file=fout)
                if errors[i] is not None:
                    print(f'  Exception in device: {e}', file=fout)
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
