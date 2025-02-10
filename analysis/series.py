import sqlite3
import shutil
from tqdm import tqdm
from os import scandir
import yaml
import util
import pickle
import datetime

def fetch_series(key, cursor):
    cursor.execute('SELECT Timestamp, Value FROM PropertyValues WHERE Device = ? AND ObjectType = ? AND ObjectId = ? AND Property = ? AND Timestamp BETWEEN ? AND ? ORDER BY Timestamp', key)
    series_raw = cursor.fetchall()
    cursor.execute('SELECT Timestamp, Value FROM LastValues WHERE Device = ? AND ObjectType = ? AND ObjectId = ? AND Property = ? AND Timestamp BETWEEN ? AND ? ORDER BY Timestamp', key)
    series_raw += cursor.fetchall()
    return series_raw

def load_fast(file='../series.pickle'):
    global tbl_data
    import os
    with open(file, 'rb') as fin:
        tbl_data = pickle.load(fin)

def fast_fetch_series(key, cursor=None):
    global tbl_data
    return tbl_data[key]

def fast_compare(val1, val2):
    lines1 = val1.split('\n')
    lines2 = val2.split('\n')
    if len(lines1) != len(lines2):
        return False
    sz = len(lines1)
    for i in range(sz):
        init_tab = 0
        while lines1[i][init_tab] == ' ':
            init_tab += 1
        line1 = lines1[i][init_tab:]
        init_tab = 0
        while lines2[i][init_tab] == ' ':
            init_tab += 1
        line2 = lines2[i][init_tab:]
        if line1.startswith('timeRemaining'):
            continue
        if line1 != line2:
            return False
    return True


def get_diff(typ, lst1, lst2, show_old):
    i1 = 0
    i2 = 0
    diff = []
    for elem in lst2:
        found = False
        for elem2 in lst1:
            if fast_compare(elem, elem2):
                found = True
                break
        if found:
            if show_old:
                diff.append((elem, 'black'))
        else:
            diff.append((elem, 'green'))
    for elem in lst1:
        found = False
        for elem2 in lst2:
            if fast_compare(elem, elem2):
                found = True
                break
        if not found:
            diff.append((elem, 'red'))
    return diff

def remove_duplicates(typ, lst):
    res = []
    lst.sort()
    prev = ''
    for elem in lst:
        if prev != '' and fast_compare(elem, prev):
            continue
        
        prev = elem
        res.append(elem)
    return res

def extra_diff(typ, lst1, lst2):
    res1 = []
    res2 = []
    keep = [True] * len(lst2)
    for elem in lst1:
        if elem[1] == 'black':
            res1.append(elem)
            continue
        inverse_color = 'red' if elem[1] == 'green' else 'green'
        first = elem[0]
        found = False
        for i in range(len(lst2)):
            if not keep[i]:
                continue
            if lst2[i][1] != inverse_color:
                continue
            if util.compare(typ['Element Type'], first, lst2[i][0]):
                keep[i] = False
                found = True
                break
        if not found:
            res1.append(elem)
    for i in range(len(lst2)):
        if keep[i]:
            res2.append(lst2[i])
    return res1, res2

def list_diff(mappings, cur, key):
    global tbl_data
    
    show_old = False
    cleanup = True
    
    obj = 'device'
    prop = 'activeCovSubscriptions'
    
    res = fast_fetch_series(key, cur)    
    items = []
    for i, elem in enumerate(res):
        if elem[1] is None:
            items.append((elem[0], ['<NULL>']))
        else:
            items.append((elem[0], sorted(util.parse_list(elem[1]))))
    for i in range(len(items)):
        time, value = items[i]
        items[i] = (time, remove_duplicates(mappings[obj][prop]['Type'], value))
    diff = [(items[0][0], list(map(lambda x: (x, 'black'), items[0][1])))]
    for i in tqdm(range(1, len(items)), leave=False):
        diff.append((items[i][0], get_diff(mappings[obj][prop]['Type'], items[i - 1][1], items[i][1], show_old)))
    
    if cleanup:
        for i in tqdm(range(1, len(items)), leave=False):
            lst1, lst2 = extra_diff(mappings[obj][prop]['Type'], diff[i - 1][1], diff[i][1])
            diff[i - 1] = diff[i - 1][0], lst1
            diff[i] = diff[i][0], lst2
    diff = list(filter(lambda x: len(x[1]) > 0, diff))
    return diff

if __name__ == "__main__":
    mappings = dict()
    for file in scandir('../mappings'):
        if not file.name.endswith('.yaml'):
            continue
        with open(file, 'r') as fin:
            obj = yaml.safe_load(fin)
            mappings.update(util.update_names(obj))
    
    mappings_extra = dict()
    for file in scandir('../mappings/other'):
        with open(file, 'r') as fin:
            obj = yaml.safe_load(fin)
            mappings_extra.update(obj)
    util.set_mappings(mappings, mappings_extra)

    TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
    TIME_FORMAT_SHORT = "%Y-%m-%d %Hh"
    start_date = datetime.datetime.strptime("2024-08-01 00:00:00.0", TIME_FORMAT)
    end_date = datetime.datetime.strptime("2024-12-01 00:00:00.0", TIME_FORMAT)    
    
    conn = sqlite3.connect('diff_v2.sqlite3')
    cursor = conn.cursor()
    
    cursor.execute('SELECT Timestamp, Value, Device, ObjectType, ObjectId, Property FROM FullValues WHERE Timestamp BETWEEN ? AND ?', (start_date, end_date))
    data = cursor.fetchall()
    tbl_data = dict()
    for elem in tqdm(data):
        value, key = elem[:2], elem[2:]
        if key not in tbl_data:
            tbl_data[key] = []
        tbl_data[key].append(value)
    
    with open('pickles/series_full.pickle', 'wb') as fout:
        pickle.dump(tbl_data, fout)
    
    conn.close()
