import yaml
import time
import datetime
import BAC0
from BAC0.core.io.IOExceptions import UnknownPropertyError
import os
from threading import Thread
import sys
import shutil
import sqlite3
import zlib
import traceback
from multiping import multi_ping

from bacpypes.basetypes import PropertyIdentifier, ObjectTypesSupported

import config
import patch
import file_reader

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

def process_device(addr, dev_id):
    print(f"Prossess device {addr}:{dev_id}")
    objects = bacnet.read(f'{addr} device {dev_id} objectList')
    print(f"Process {len(objects)} objects on device {addr}:{dev_id} (trying ReadPropertyMultiple)")
    results = dict()
    for obj in objects:
        obj_name = obj[0] + ':' + str(obj[1])
        if obj[0] not in mappings:
            results[obj_name] = f'Skipping object type {obj[0]} (mapping not implemented)'
            continue
        mapping = mappings[obj[0]]
        try:
            vals = bacnet.readMultiple(f'{addr} {obj[0]} {obj[1]} {" ".join(mapping.keys())}')
            values = dict(zip(mapping.keys(), vals))
        except Exception as e: # TODO: find exception for "readMultiple not supported"
            print(f'ReadPropertyMultiple not supported, fallback to ReadProperty for {addr}:{dev_id}')
            print('Reason:')
            print(traceback.format_exc())
            print('End of error', flush=True)
            values = dict()
            for key in mapping:
                try:
                    print('Reading', key, flush=True)
                    values[key] = bacnet.read(f'{addr} {obj[0]} {obj[1]} {key}')
                except UnknownPropertyError:
                    values[key] = None
                except Exception as e:
                    values[key] = traceback.format_exc()
                time.sleep(config.property_delay)
        results[obj_name] = values
    return results

def switch_db_file(new_db_file):
    print('Switching to a new database file', flush=True)
    try:
        old_db_files = []
        for elem in os.scandir(config.base_dir):
            if elem.name.endswith('.sqlite3') and elem.name != config.db_base_file:
                print('Found old database file:', elem.path, flush=True)
                old_db_files.append(elem.path)
        for file in old_db_files:
            compress = zlib.compressobj()
            with open(file, 'rb') as fin:
                with open(file + '.zip', 'wb') as fout:
                    while True:
                        data = fin.read(65536)
                        if len(data) == 0:
                            break
                        fout.write(compress.compress(data))
                    fout.write(compress.flush())
            print('Successfully compressed file to', file + '.zip', flush=True)
            shutil.move(file, file + '_compressed')
    except Exception as e:
        print('Exception while compressing old databases:')
        print(traceback.format_exc())
        print('End of error', flush=True)
    shutil.copyfile(os.path.join(config.base_dir, config.db_base_file), new_db_file)
    print('Created new database file', new_db_file, flush=True)

mappings = dict()
for file in os.scandir('../mappings'):
    if not file.name.endswith('.yaml'):
        continue
    if file.name in ['Binary Value.yaml', 'Binary Input.yaml', 'Binary Output.yaml', 'Analog Value.yaml', 'Analog Input.yaml', 'Analog Output.yaml']:
        continue
    with open(file, 'r') as fin:
        obj = yaml.safe_load(fin)
        mappings.update(update_names(obj))

if verify_mapping(mappings):
    sys.exit()

BAC0.log_level(stdout=config.log_level)
bacnet = BAC0.lite(ip=config.probe_ip)

discovered = []

timestamp = datetime.datetime.now()

usedTxtFile = False
try:
    # Initialize database file
    db_file = os.path.join(config.base_dir, config.db_file.format(timestamp.strftime('%Y-%m-%d')))
    if not os.path.exists(db_file):
        switch_db_file(db_file)
    db = sqlite3.connect(db_file, isolation_level='EXCLUSIVE')
    cur = db.cursor()
except sqlite3.Error as e:
    usedTxtFile = True
    with open(os.path.join(config.base_dir, config.output_filename), 'a') as fout:
        print(timestamp.strftime('%Y/%m/%d %H:%M:%S'), file=fout) 
        print('Exception while writing to the database:', file=fout)
        print(traceback.format_exc(), file=fout)

ip_list = set(config.ip_whitelist).difference(config.ip_blacklist)
ip_count = len(ip_list)
print(f'Pinging {ip_count} devices', flush=True)
ip_list = multi_ping(ip_list, timeout=2, retry=3)[0].keys()
print(f'Ping finished, proceeding with {len(ip_list)} devices out of {ip_count}', flush=True)

for ip in ip_list:
    try:
        # Add device to database, if not already present
        cur.execute('SELECT Id FROM Devices WHERE Address = ?', (ip,))
        row = cur.fetchone()
        if row is None:
            cur.execute('INSERT INTO Devices(Address) VALUES (?)', (ip,))
            dev_id = cur.lastrowid
        else:
            dev_id = row[0]
    
        # Discover the device
        try:
            dev_bacnet_id = bacnet.read(f'{ip} device {0x3fffff} objectIdentifier')[1]
        except Exception as e:
            cur.execute('INSERT INTO Exceptions(Timestamp, Device, Text) VALUES (?, ?, ?)', (timestamp, dev_id, traceback.format_exc()))
            continue
        
        # Read the device properties
        try:
            dev_data = process_device(ip, dev_bacnet_id)
        except Exception as e:
            cur.execute('INSERT INTO Exceptions(Timestamp, Device, Text) VALUES (?, ?, ?)', (timestamp, dev_id, traceback.format_exc()))
            continue
        
        # Write collected data to the database
        for obj_name in dev_data:
            obj_data = dev_data[obj_name]
            if type(obj_data) == str:
                print(obj_data, flush=True)
                continue
            obj_type, bacnet_obj_id = obj_name.split(':')
            cur.execute('SELECT Id FROM Objects WHERE Device = ? AND Type = ? AND BACnetId = ?', (dev_id, obj_type, bacnet_obj_id))
            row = cur.fetchone()
            if row is None:
                cur.execute('INSERT INTO Objects(Device, Type, BACnetId) VALUES (?, ?, ?)', (dev_id, obj_type, bacnet_obj_id))
                obj_id = cur.lastrowid
            else:
                obj_id = row[0]
            for prop_name in obj_data:
                cur.execute('SELECT Id FROM Properties WHERE Object = ? AND Name = ?', (obj_id, prop_name))
                row = cur.fetchone()
                if row is None:
                    cur.execute('INSERT INTO Properties(Object, Name) VALUES (?, ?)', (obj_id, prop_name))
                    prop_id = cur.lastrowid
                else:
                    prop_id = row[0]
                value = obj_data[prop_name]
                if value is not None:
                    value = str(value)
                cur.execute('INSERT INTO PropertyValues(Timestamp, Property, Value) VALUES (?, ?, ?)', (timestamp, prop_id, value))
        db.commit()
        
    except sqlite3.Error as e:
        with open(os.path.join(config.base_dir, config.output_filename), 'a') as fout:
            if not usedTxtFile:
                print(timestamp.strftime('%Y/%m/%d %H:%M:%S'), file=fout)
            usedTxtFile = True
            print('Exception while writing to the database:', file=fout)
            print(traceback.format_exc(), file=fout)
            print(f'{ip}:{dev_bacnet_id}', file=fout)
            if isinstance(obj_data, str):
                print(f'    do not inspect; {obj_data}', file=fout)
                continue
            for obj_name in dev_data:
                print('  ' + obj_name, file=fout)
                obj_data = dev_data[obj_name]
                try:
                    if type(obj_data) == str:
                        print('    ' + obj_data, file=fout)
                        continue
                    for prop_name in obj_data:
                        print('    ' + prop_name, end=': ', file=fout)
                        if obj_data[prop_name] is None:
                            print('property unavailable', file=fout)
                        else:
                            print(obj_data[prop_name], file=fout)
                except Exception as e:
                    print('unhandled error:', file=fout)
                    print(traceback.format_exc(), file=fout)
        
    # Wait before polling the next device to avoid network overload
    time.sleep(config.device_delay)

if usedTxtFile:
    with open(os.path.join(config.base_dir, config.output_filename), 'a') as fout:
        print("\n\nEOF.", file=fout)

# Read files from the devices
# TODO: move this to the device cycle
bacnet.disconnect()  # We need a custom derived class in file_reader, so close here and reopen there
try:
    file_reader.fetch_files(db, timestamp)
except sqlite3.Error as e:
    print('Error while accessing database for files:')
    print(traceback.format_exc())
    print('End of error', flush=True)
db.close()


# TODO: start with derived version from file_reader
try:
    bacnet.disconnect()
except:
    pass
