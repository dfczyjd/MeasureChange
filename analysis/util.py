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
from icmplib import multiping

from bacpypes.basetypes import PropertyIdentifier, ObjectTypesSupported

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

def get_type(mappings, key):
    _, obj, _, prop = elem
    typ = mappings[obj][prop]['Type']
    if type(typ) == str:
        return typ
    return typ['Name']

def map_bool(item, val_set):
    if item is None:
        return 0.75
    if item in val_set:
        return val_set[item]
    return 0.25

def convert_bool(series):
    value_sets = [
        {'inactive': 0, 'active': 1},
        {'normal': 0, 'inversed': 1},
        {'False': 0, 'True': 1},
        {'0': 0, '1': 1},
        
        {'Fail': 0.25}
    ]
    values = set(series)
    best = (-1, -1)
    for i, val_set in enumerate(value_sets):
        sz = len(values.intersection(val_set.keys()))
        if sz > best[1]:
            best = (i, sz)
    if best[1] == 0:
        print('Unexpected bool set:' + str(values))
    return list(map(lambda x: map_bool(x, value_sets[best[0]]), series))

def enumerate_series(series, gaps):
    values = set(series)
    if 'None' in values:
        values.remove('None')
    if None in values:
        values.remove(None)
    values = dict(zip(sorted(values), map(lambda x: x / 8, range(1, len(values) + 1))))
    res = [1.0]
    for i, elem in enumerate(series):
        if gaps[i]:
            res.append(1.0)
        elif elem == 'None' or elem is None:
            res.append(0.0)
        else:
            res.append(values[elem])
    return res

def parse_array(arr, length):
    exceptions = ['0.0', 'noFaultDetected', '', 'Unoccupied', 'False', 'Drivers.DynetNetwork.Lighting_Logical_Control.points.Area 14.Preset', 'inactive', 'active', 'Drivers.DynetNetwork.Lighting_Logical_Control.points.Area 15.Occupancy', 'noUnits']
    
    if arr is None:
        return [None] * length
    if arr.strip().startswith('length'):
        lines = arr.split('\n')
        res = []
        for line in lines[2::2]:
            typ, val = line.strip().split(' = ')
            if typ == 'null':
                val = 'None'
            res.append(val)
        assert len(res) == length
        return res
    else:
        if not set(arr[1:-1]).issubset({'0', '1', ' ', ','}):
            if arr in exceptions:
                return ['Fail'] * length
            raise Exception(f'Failed to parse {arr}')
        res = list(map(str.strip, arr[1:-1].split(',')))
        if len(res) != length:
            if arr in exceptions:
                return ['Fail'] * length
            raise Exception(f'Failed to parse {repr(arr)}')
        return res

def parse_list(lst):
    exceptions = ['3000', '1', '3', 'TUE_Verd_Min1_2_Midden_Noord_110504', 'Tridium 4.4.92.2', 'segmentedBoth', '180', '14', 'Local BACnet Device object']
    
    if lst is None:
        return None
    res = []
    curr = []
    lines = lst.split('\n')
    if len(lines) == 1:
        cnt = 0
        i = 1
        while i < len(lst):
            sym = lst[i]
            if sym == ']':
                if len(curr) > 0:
                    res.append(''.join(curr))
                break
            if sym == ',' and cnt == 0:
                res.append(''.join(curr))
                curr = []
                i += 2
                continue
            if sym == '(':
                cnt += 1
            elif sym == ')':
                cnt -= 1
            curr.append(sym)
            i += 1
        else:
            if lst not in exceptions:
                print(f'Failed to parse {repr(lst)}')
                return res
        if cnt != 0:
            raise Exception(f'Failed to parse {repr(lst)}')
        return res
                
    for line in lines:
        if line.startswith('['):
            line = line[1:]
        if line == ']':
            res.append('\n'.join(curr))
        if line.startswith(','):
            res.append('\n'.join(curr))
            curr = [line[2:]]
        else:
            curr.append(line)
    if len(res) == 0 and lst != '[]':
        raise Exception(f'Failed to parse {repr(lst)}')
    return res

def count_keys(obj):
    if type(obj) != dict:
        return 0
    cnt = 0
    for key in obj:
        cnt += 1
        cnt += count_keys(obj[key])
    return cnt

def parse_object(obj):
    if obj is None:
        return None
    if obj == '<NULL>':
        return None
    res = dict()
    init_tab = 0
    while obj[init_tab * 4] == ' ':
        init_tab += 1
    lines = obj.split('\n')
    curr = dict()
    keys = []
    
    for line in lines:
        if line.strip() == '':
            continue
        tab = 0
        while line[tab * 4] == ' ':
            tab += 1
        line = line[tab * 4:]
        tab -= init_tab
        if tab >= len(keys) - 1:
            if tab > len(keys) - 1:
                keys.append([])
            if '=' in line:
                keys[-1].append(line.split(' = '))
            else:
                keys[-1].append(line)
        else:
            for i in range(len(keys) - 1, tab, -1):
                last = dict(keys.pop())
                keys[-1][-1] = (keys[-1][-1], last)
            if '=' in line:
                keys[-1].append(line.split(' = '))
            else:
                keys[-1].append(line)
    while len(keys) > 1:
        last = dict(keys.pop())
        keys[-1][-1] = (keys[-1][-1], last)
    res = dict(keys[-1])
    cnt = count_keys(res)
    if cnt != len(lines):
        raise Exception(f'Failed to parse {obj}')
    return res

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
        print(repr(val1))
        print(repr(val2))
        print(traceback.format_exc())
        input()
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
            data1 = parse_array(val1, typ['Length'])
            data2 = parse_array(val2, typ['Length'])
            for i in range(typ['Length']):
                if not compare(typ['Element Type'], data1[i], data2[i]):
                    return False
            return True
        if typ['Name'] == 'list':
            if val1 == '' or val2 == '':
                return val1 == val2
            data1 = parse_list(val1)
            data2 = parse_list(val2)
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
            data1 = parse_object(val1)
            data2 = parse_object(val2)
            return compare_objects(mapping, data1, data2)
        print('Unknown type:', typ)
        return val1 == val2
    except Exception as e:
        print(repr(typ), flush=True)
        print('Value 1')
        print(repr(val1), flush=True)
        print('Value 2')
        print(repr(val2), flush=True)
        print(traceback.format_exc())
        input()
        return False

def get_item_by_month(item_type, date, path=''):
    if item_type == 'db':
        prefix = 'diff_v2'
        suffix = '.sqlite3'
    elif item_type == 'pickle':
        prefix = 'pickles/series'
        suffix = '.pickle'
    else:
        raise Exception(f'Unknown type: {item_type}')
    month = date.strftime('%b').lower()
    return os.path.join(path, prefix + '_' + month + suffix)

def set_mappings(mp, mp_extra):
    global mappings, mappings_extra
    mappings = mp
    mappings_extra = mp_extra