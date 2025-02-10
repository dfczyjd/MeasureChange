import zlib
import os
import sqlite3
import shutil
from tqdm import tqdm
import sys
import traceback
import yaml

import util

def compare_objects(mapping, val1, val2):
    if val1 == val2:
        return True
    if val1 is None or val2 is None:
        return False
    try:
        for key in mapping:
            if type(mapping[key]) == str or 'Name' in mapping[key]:
                if not compare(mapping[key], val1[key], val2[key]):
                    return False              
            else:
                if not compare_objects(mapping[key], val1[key], val2[key]):
                    return False
        return True
    except Exception as e:
        with open('fault.txt', 'a') as fout:
            print(repr(val1), file=fout)
            print(repr(val2), file=fout)
            print(traceback.format_exc(), file=fout)
        return False

def compare(typ, val1, val2):
    if val1 == val2:
        return True
    if val1 is None or val2 is None:
        return False
    global mappings, mappings_extra
    try:
        if typ in ['number', 'datetime', 'bool', 'other']:
            return val1 == val2
        if typ['Name'] == 'array':
            if val1 == '' or val2 == '':
                return val1 == val2
            data1 = util.parse_array(val1, typ['Length'])
            data2 = util.parse_array(val2, typ['Length'])
            for i in range(typ['Length']):
                if not compare(typ['Element Type'], data1[i], data2[i]):
                    return False
            return True
        if typ['Name'] == 'list':
            if val1 == '' or val2 == '':
                return val1 == val2
            data1 = util.parse_list(val1)
            data2 = util.parse_list(val2)
            if len(data1) != len(data2):
                return False
            data1.sort()
            data2.sort()
            for i in range(len(data1)):
                if not compare(typ['Element Type'], data1[i], data2[i]):
                    return False
            return True
        if typ['Name'] == 'object ref':
            return val1 == val2
        if typ['Name'] == 'object':
            if val1 == '' or val2 == '':
                return val1 == val2
            mapping = mappings_extra[typ['Type']]
            data1 = util.parse_object(val1)
            data2 = util.parse_object(val2)
            return compare_objects(mapping, data1, data2)
        print('Unknown type:', typ)
        return val1 == val2
    except Exception as e:
        with open('fault.txt', 'a') as fout:
            print(repr(typ), flush=True, file=fout)
            print('Value 1', file=fout)
            print(repr(val1), flush=True, file=fout)
            print('Value 2', file=fout)
            print(repr(val2), flush=True, file=fout)
            print(traceback.format_exc(), file=fout)
        return False

print('Reading mapping files', flush=True)
mappings = dict()
for file in os.scandir('../mappings'):
    if not file.name.endswith('.yaml'):
        continue
    with open(file, 'r') as fin:
        obj = yaml.safe_load(fin)
        mappings.update(util.update_names(obj))
mappings_extra = dict()
for file in os.scandir('../mappings/other'):
    with open(file, 'r') as fin:
        obj = yaml.safe_load(fin)
        mappings_extra.update(obj)

if not os.path.exists('diff_v2.sqlite3'):
    shutil.copyfile('base.sqlite3', 'diff_v2.sqlite3')

main_db = sqlite3.connect('diff_v2.sqlite3', isolation_level='EXCLUSIVE')
main_cur = main_db.cursor()

print('Fetching data from last run', flush=True)
last_values = dict()
main_cur.execute('SELECT Device, ObjectType, ObjectId, Property, Value, Timestamp FROM LastValues')
prev_lasts = main_cur.fetchall()
last_values = dict(map(lambda row: (row[:4], row[4:]), prev_lasts))
if len(last_values) == 0:
    print('No data found from last run', flush=True)
else:
    for elem in tqdm(prev_lasts, leave=False):
        main_cur.execute('INSERT INTO PropertyValues (Device, ObjectType, ObjectId, Property, Value, Timestamp) VALUES (?, ?, ?, ?, ?, ?)', elem)
    main_cur.execute('DELETE FROM LastValues WHERE 1=1')
    main_db.commit()

for file in tqdm(os.listdir('data'), position=0):
    if not file.endswith('.sqlite3'):
        continue
    conn = sqlite3.connect('data/' + file, isolation_level='EXCLUSIVE')
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT Timestamp FROM PropertyValues')
    times = cur.fetchall()
    for time in tqdm(times, position=1, leave=False):
        time = time[0]
        cur.execute('SELECT Device, ObjectType, ObjectId, Property, Value FROM PropertyValues WHERE Timestamp = ?', (time,))
        snap = cur.fetchall()
        for elem in tqdm(snap, position=2, leave=False):
            key, value = elem[:-1], elem[-1]
            if type(value) == str and value.startswith('Traceback'):
                continue
            if key not in last_values:
                last_values[key] = (value, time)
                continue
            _, obj, _, prop = key
            if last_values[key][0] == value:
                continue
            if prop in mappings[obj] and compare(mappings[obj][prop]['Type'], last_values[key][0], value):
                continue
            main_cur.execute('INSERT INTO PropertyValues (Timestamp, Device, ObjectType, ObjectId, Property, Value) VALUES (?, ?, ?, ?, ?, ?)',
                             (last_values[key][1],) + key + (last_values[key][0],))            
            last_values[key] = (value, time)
    main_db.commit()
    conn.close()

print('Updating final values', flush=True)
main_cur.execute('DELETE FROM LastValues WHERE 1=1')
for key in tqdm(last_values):
    value, time = last_values[key]
    try:
        main_cur.execute('INSERT INTO LastValues (Timestamp, Device, ObjectType, ObjectId, Property, Value) VALUES (?, ?, ?, ?, ?, ?)',
                         (time,) + key + (value,))
    except Exception as e:
        print(e)
        print(time, key, value)
        raise e
main_db.commit()
main_db.close()
