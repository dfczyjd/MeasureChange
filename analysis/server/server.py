import flask
from os import scandir
import sqlite3
import sys
import yaml
import json
import matplotlib.pyplot as plt
import datetime
import time
from matplotlib.dates import date2num
from matplotlib.colors import ListedColormap
from tqdm import tqdm

sys.path.append('..')
import series
import util

app = flask.Flask(__name__)

def get_diff(typ, lst1, lst2, show_old):
    i1 = 0
    i2 = 0
    diff = []
    ln1 = len(lst1)
    ln2 = len(lst2)
    
    found_at = [False] * ln1
    for i, elem in enumerate(lst2):
        found = False
        for j, elem2 in enumerate(lst1):
            if found_at[j]:
                continue
            if util.compare(typ['Element Type'], elem, elem2):
                found = True
                found_at[j] = True
                break
        if found:
            if show_old:
                diff.append((elem, 'black'))
        else:
            diff.append((elem, 'green'))
    
    found_at = [False] * ln2
    for i, elem in enumerate(lst1):
        found = False
        for j, elem2 in enumerate(lst2):
            if found_at[j]:
                continue
            if util.compare(typ['Element Type'], elem, elem2):
                found = True
                found_at[j] = True
                break
        if not found:
            diff.append((elem, 'red'))
    return diff

def remove_duplicates(typ, lst):
    res = []
    lst.sort()
    prev = ''
    for elem in lst:
        if prev != '' and util.compare(typ['Element Type'], elem, prev):
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

@app.route("/fast_list")
def fast_list_diff():
    feature_id = flask.request.args.get('id', '')
    extra_clause = flask.request.args.get('cond', '1=1')
    offset = flask.request.args.get('page', '0')
    
    conn = sqlite3.connect('../diff_v2.sqlite3')
    cur = conn.cursor()
    
    cur.execute(f'''SELECT DISTINCT Feature FROM ListSeries
                       WHERE {extra_clause}
                       GROUP BY Feature
                       HAVING COUNT(DISTINCT Timestamp) > 1
                       LIMIT 10 OFFSET ?''', (offset,))
    features = list(map(lambda x: x[0], cur.fetchall()))

    if feature_id == '':
        page = flask.render_template('list.html', features=enumerate(features), results=False)
    else:
        feature = features[int(feature_id)]
        cur.execute('SELECT Timestamp, Value, Color FROM ListSeries WHERE Feature = ? ORDER BY Timestamp, ItemId', (feature,))
        data = cur.fetchall()
        items = []
        item = [(data[0][1], data[0][2])]
        last_time = data[0][0]
        for i in range(1, len(data)):
            time, value, color = data[i]
            if time != last_time:
                items.append((last_time, item))
                item = []
                last_time = time
            item.append((value, color))
        items.append((last_time, item))
        page = flask.render_template('list.html',
                                     features=enumerate(features),
                                     feat_id=int(feature_id),
                                     results=True,
                                     items=items)        
    
    conn.close()
    return page

@app.route("/list")
def list_diff():
    global mappings
    feature_id = flask.request.args.get('id', '')
    show_old = flask.request.args.get('show_old', '0') == '1'
    cleanup = flask.request.args.get('cleanup', '0') == '1'
    compare = flask.request.args.get('compare', '1') == '1'
    
    conn = sqlite3.connect('../diff_v2.sqlite3')
    cur = conn.cursor()
    
    cur.execute('SELECT DISTINCT Device, ObjectType, ObjectId, Property FROM PropertyValues ORDER BY Device, ObjectType, ObjectId, Property')
    db_items = cur.fetchall()
    
    features = []
    for elem in db_items:
        dev, obj, obj_id, prop = elem
        if prop in mappings[obj]:
            if type(mappings[obj][prop]['Type']) == str:
                continue
            if mappings[obj][prop]['Type']['Name'] == 'list':
                features.append(':'.join([dev, obj, str(obj_id), prop]))
    
    if feature_id == '':
        page = flask.render_template('list.html', features=enumerate(features), results=False)
    else:
        key = tuple(features[int(feature_id)].split(':'))
        _, obj, _, prop = key
        res = series.fetch_series(key, cur)
        items = []
        for i, elem in enumerate(res):
            if elem[1] is None:
                items.append((elem[0], ['<NULL>']))
            else:
                items.append((elem[0], sorted(util.parse_list(elem[1]))))
        if cleanup:
            for i in range(len(items)):
                time, value = items[i]
                items[i] = (time, remove_duplicates(mappings[obj][prop]['Type'], value))
        if compare:
            diff = [(items[0][0], list(map(lambda x: (x, 'black'), items[0][1])))]
            for i in tqdm(range(1, len(items))):
                diff.append((items[i][0], get_diff(mappings[obj][prop]['Type'], items[i - 1][1], items[i][1], show_old)))
            
            if cleanup:
                for i in tqdm(range(1, len(items))):
                    lst1, lst2 = extra_diff(mappings[obj][prop]['Type'], diff[i - 1][1], diff[i][1])
                    diff[i - 1] = diff[i - 1][0], lst1
                    diff[i] = diff[i][0], lst2
            diff = list(filter(lambda x: len(x[1]) > 0, diff))
        else:
            diff = [(item[0], list(map(lambda x: (x, 'black'), item[1]))) for item in items]
        page = flask.render_template('list.html',
                                            features=enumerate(features),
                                            feat_id=feature_id,
                                            results=True,
                                            items=diff)
    
    conn.close()
    return page

def expand_series(timestamps, values):
    global start_date, end_date, date_range, gaps
    res = []
    values = list(values)
    timestamps = list(map(lambda t: datetime.datetime.strptime(t, TIME_FORMAT), timestamps))
    if timestamps[0] != start_date:
        timestamps = [start_date] + timestamps
        values = ['None'] + values
    for i in range(len(timestamps)):
        if timestamps[i].minute != 0:
            timestamps.pop(i)
            values.pop(i)
            break
    intervals = zip(timestamps, timestamps[1:] + [end_date])
    
    for i, (int_start, int_end) in enumerate(intervals):
        # Align timestamp with 2-hour grid
        int_start = int_start.replace(second=0, microsecond=0)
        int_end = int_end.replace(second=0, microsecond=0)
        
        delta = int((int_end - int_start).total_seconds() / DELAY)
        res += [values[i]] * delta
    
    return res

def render_bool_diagram(values, labels, time_ticks):
    global date_range
    new_cmap = ListedColormap([
        [1.0, 1.0, 1.0, 1.0],  # false/off (white)
        [1.0, 0.0, 0.0, 1.0],  # invalid (red)
        [0.0, 0.0, 1.0, 1.0],  # data not recorded(TBA)
        [0.5, 0.5, 0.5, 1.0],  # missing (gray)
        [0.0, 0.0, 0.0, 1.0]   # true/on (black) 
    ])
    
    plt.figure(figsize=(int(len(date_range) * 0.1), len(labels)))
    plt.pcolormesh(range(len(date_range) + 1), range(len(labels) + 1), values, cmap=new_cmap)
    labels_time, ticks_time = zip(*sorted(time_ticks))
    plt.xticks(ticks_time, labels_time, rotation='vertical')
    plt.yticks([x + 0.5 for x in range(len(labels))], labels)
    plt.savefig('static/diagram.png')

@app.route('/all')
def overall_diagram():
    global start_date, end_date, gaps
    
    sort_key_arg = flask.request.args.get('sort', '')
    if sort_key_arg == 'prop':
        sort_key = lambda k: (k[3], k[0], k[1], k[2])
    elif sort_key_arg == 'obj':
        sort_key = lambda k: (k[1], k[2], k[3], k[0])
    elif sort_key_arg == 'dev':
        sort_key = lambda k: k
    else:
        sort_key = None
    
    conn = sqlite3.connect('../diff_v2.sqlite3')
    cur = conn.cursor()
    
    diagram = []
    labels = []
    time_ticks = set()
    
    skipped = [
        'relinquishDefault',
        'activeCovSubscriptions'
    ]
    
    features = []
    for key in ['bool', 'number', 'other', 'object ref']:
        if key in features_by_type:
            features += features_by_type[key]
    
    if sort_key is not None:
        features = sorted(features, key=sort_key)    
    
    props = set()
    objs = set()
    
    for key in tqdm(features):
        if key[-1] in skipped:
            continue
        res = series.fast_fetch_series(key, cur)
        
        times, values = zip(*res)
        if len(set(values)) == 1:
            continue
        
        objs.add(key[1])
        props.add(key[3])        
        
        time_labels = []
        for elem in times:
            time = datetime.datetime.strptime(elem, TIME_FORMAT).replace(second=0, microsecond=0)
            start = start_date.replace(second=0, microsecond=0)
            tick = int((time - start).total_seconds() / DELAY)
            time_labels.append((datetime.datetime.strftime(time, TIME_FORMAT_SHORT), tick))
        time_ticks.update(time_labels)
        
        labels.append(f'{key[0]}:{key[1]}:{key[2]}:{key[3]}')
        exp = expand_series(times, values)
        diagram.append(util.enumerate_series(exp, gaps))
    
    conn.close()
    
    new_cmap = ListedColormap([
        [0.5, 0.5, 0.5, 1.0],   # Value is missing
        [1.0, 0.0, 0.0, 1.0],
        [0.0, 0.0, 1.0, 1.0],
        [1.0, 1.0, 0.0, 1.0],
        [0.0, 1.0, 1.0, 1.0],
        [0.0, 0.0, 0.0, 1.0],
        [1.0, 0.0, 1.0, 1.0],
        #[1.0, 1.0, 0.0, 1.0],   # Data not recorded
        [0.25, 0.25, 0.25, 1.0],   # Data not recorded
    ])

    plt.figure(figsize=(int(len(date_range) * 0.1), len(labels)))
    plt.pcolormesh(range(len(date_range) + 1), range(len(labels) + 1), diagram, cmap=new_cmap)
    labels_time, ticks_time = zip(*sorted(time_ticks))
    plt.xticks(ticks_time, labels_time, rotation='vertical')
    plt.yticks([x + 0.5 for x in range(len(labels))], labels)
    plt.savefig('static/diagram.png')
    return flask.render_template('bool.html', features=enumerate(features), results=True)    

@app.route('/bool')
def bool_diff():
    sort_key_arg = flask.request.args.get('sort', '')
    if sort_key_arg == 'prop':
        sort_key = lambda k: (k[3], k[0], k[1], k[2])
    elif sort_key_arg == 'obj':
        sort_key = lambda k: (k[1], k[2], k[3], k[0])
    elif sort_key_arg == 'dev':
        sort_key = lambda k: k
    else:
        sort_key = None
    
    conn = sqlite3.connect('../diff_v2.sqlite3')
    cur = conn.cursor()
    
    bool_diagram = []
    labels = []
    time_ticks = set()
    
    if sort_key is None:
        features = features_by_type['bool']
    else:
        features = sorted(features_by_type['bool'], key=sort_key)
    
    for key in features:
        res = series.fast_fetch_series(key, cur)
        
        times, values = zip(*res)
        values = util.convert_bool(values)
        
        time_labels = []
        for elem in times:
            time = datetime.datetime.strptime(elem, TIME_FORMAT).replace(second=0, microsecond=0)
            start = start_date.replace(second=0, microsecond=0)
            tick = int((time - start).total_seconds() / DELAY)
            time_labels.append((datetime.datetime.strftime(time, TIME_FORMAT_SHORT), tick))
        time_ticks.update(time_labels)
        
        labels.append(f'{key[0]}:{key[1]}:{key[2]}:{key[3]}')
        bool_diagram.append(expand_series(times, values))
    
    conn.close()
    
    render_bool_diagram(bool_diagram, labels, time_ticks)
    return flask.render_template('bool.html', features=enumerate(features), results=True)

@app.route('/array')
def array_diff():
    global mappings, gaps
    prop_name = flask.request.args.get('prop', '')
    
    conn = sqlite3.connect('../diff_v2_aug.sqlite3')
    cur = conn.cursor()
    
    cur.execute('SELECT Device, ObjectType, ObjectId, Property FROM FullValues GROUP BY Device, ObjectType, ObjectId, Property HAVING COUNT(*) > 1')
    db_items = cur.fetchall()
    
    features = []
    props = set()
    length = 0
    for elem in db_items:
        dev, obj, obj_id, prop = elem
        if prop in mappings[obj]:
            if type(mappings[obj][prop]['Type']) == str:
                continue
            if mappings[obj][prop]['Type']['Name'] == 'array':
                props.add(prop)
                if prop == prop_name:
                    length = mappings[obj][prop]['Type']['Length']
                    features.append(':'.join([dev, obj, str(obj_id), prop]))
    
    if prop_name == '':
        page = flask.render_template('array.html', props=props, results=False)
    else:
        diagram_data = []
        labels = []
        time_ticks = set()
        
        fetch_values = dict()
        for feat in features:
            key = feat.split(':')
            key[2] = int(key[2])
            value = series.fast_fetch_series(tuple(key), cur)
            fetch_values[feat] = value
        
        for i in range(length):
            for feat in features:
                key = feat.split(':')
                _, obj, _, prop = key
                res = fetch_values[feat]
                items = list(map(lambda x: (x[0], util.parse_array(x[1], length)), res))

                times = list(map(lambda x: x[0], items))
                values = list(map(lambda x: x[1][i], items))
                values = util.convert_bool(values)
                
                time_labels = []
                for elem in times:
                    time = datetime.datetime.strptime(elem, TIME_FORMAT).replace(second=0, microsecond=0)
                    start = start_date.replace(second=0, microsecond=0)
                    tick = int((time - start).total_seconds() / DELAY)
                    time_labels.append((datetime.datetime.strftime(time, TIME_FORMAT_SHORT), tick))
                time_ticks.update(time_labels)
                
                labels.append(feat + ' #' + str(i))
                row = expand_series(times, values)
                diagram_data.append(util.enumerate_series(row, gaps))
            labels.append('')
            diagram_data.append([0.0] * (len(date_range) + 1))
        labels.pop()
        diagram_data.pop()

        render_bool_diagram(diagram_data, labels, time_ticks)
        page = flask.render_template('array.html',
                                     props=props,
                                     prop_name=prop_name,
                                     results=True)
    
    conn.close()
    return page

def shorten_time(str_time):
    dt_time = datetime.datetime.strptime(str_time, TIME_FORMAT)
    short_time = datetime.datetime.strftime(dt_time, TIME_FORMAT_SHORT)
    
    return short_time

time_labels = None
times = None
last_pickle = None

@app.route('/diff')
def snapshot_diff():
    global times, time_labels, last_pickle

    conn = sqlite3.connect('../diff_v2.sqlite3')
    cur = conn.cursor()    
    
    if time_labels is None:
        cur.execute('SELECT DISTINCT Timestamp FROM PropertyValues')
        times = cur.fetchall()
        
        time_labels = list(enumerate(map(lambda x: shorten_time(x[0]), times)))
    
    time1 = flask.request.args.get('first', '')
    time2 = flask.request.args.get('second', '')
    if time1 == '' or time2 == '':
        conn.close()
        return flask.render_template('diff.html', times=time_labels, results=False, showAll=False)
    showAll = (flask.request.args.get('showAll', '') == 'on')
    extra_clause = flask.request.args.get('extra', '1=1')
    
    time_from = times[int(time1) + 1][0]
    time_to = times[int(time2)][0]
    
    pickle = util.get_item_by_month('pickle', datetime.datetime.strptime(time_from, TIME_FORMAT), '..')
    if pickle != last_pickle:
        last_pickle = pickle
        series.load_fast(pickle)
    
    query_full = '''
    SELECT Timestamp, Device, ObjectType, ObjectId, Property, Value FROM FullValues
        WHERE Timestamp BETWEEN ? AND ?
        AND Property NOT IN ('presentValue', 'priorityArray'{0})
        AND {1}
        --UNION SELECT Timestamp, Device, ObjectType, ObjectId, 'presentValue', Value FROM PresentValues
        --    WHERE Timestamp BETWEEN ? AND ?
        --    AND {1}
        ORDER BY Device, ObjectType, ObjectId, Timestamp
    '''.format('' if showAll else ", 'activeCovSubscriptions'", extra_clause)
    query_item = '''
    SELECT Timestamp, Value FROM FullValues
        WHERE Timestamp < ?
            AND Device == ?
            AND ObjectType == ?
            AND ObjectId == ?
            AND Property == ?
        ORDER BY Timestamp DESC
    '''
    
    cur.execute(query_full, (time_from, time_to))#, time_from, time_to))
    data = list(map(lambda x: (shorten_time(x[0]),) + x[1:], cur.fetchall()))
    
    changes = dict()
    for elem in tqdm(data):
        time, dev, obj_type, obj_id, prop, val = elem
        if time == '2024-08-22 18h':
            continue
        obj = f'{obj_type}:{obj_id}'
        if obj_type not in mappings or prop not in mappings[obj_type]:
            continue
        if dev not in changes:
            changes[dev] = dict()
        if obj not in changes[dev]:
            changes[dev][obj] = dict()
        if prop not in changes[dev][obj]:
            prev = list(filter(lambda x: x[0] < time_from, series.fast_fetch_series((dev, obj_type, obj_id, prop))))
            if len(prev) > 0:
                time_prev, val_prev = prev[-1]
            else:
                time_prev = 'Before'
                val_prev = 'Missing'
            changes[dev][obj][prop] = [(time_prev, val_prev)]
        changes[dev][obj][prop].append((time, val))            

    conn.close()
    
    return flask.render_template('diff.html',
                                 times=time_labels,
                                 results=True,
                                 first=int(time1),
                                 second=int(time2),
                                 showAll=showAll,
                                 data=changes)

@app.route('/number')
def number_diff():
    conn = sqlite3.connect('../diff_v2.sqlite3')
    cur = conn.cursor()
    
    query = '''
    SELECT Device, ObjectType, ObjectId, Property FROM FullValues
	    WHERE Property = 'presentValue'
		    AND ObjectType LIKE 'analog%'
            AND Timestamp BETWEEN ? AND ?
	    GROUP BY Device, ObjectType, ObjectId
		    HAVING COUNT(Value) == 2
            AND MAX(CAST(Value AS float)) < 100
             --AND COUNT(DISTINCT Value) * 5 < COUNT(Value)
    '''
    cur.execute(query, (start_date, end_date))
    features = cur.fetchall()
    
    items = []
    time_ticks = set()
    
    for key in tqdm(features):
        values = series.fast_fetch_series(key, cur)
        unix_time = lambda x: time.mktime(datetime.datetime.strptime(x, TIME_FORMAT).timetuple())
        time_ticks.update(map(lambda x: (shorten_time(x[0]), unix_time(x[0])), values))
        try:
            values = list(zip(*map(lambda x: [unix_time(x[0]), float(x[1])], values)))
            items.append((f'{key[0]}:{key[1]}:{key[2]}:{key[3]}', values))
        except:
            pass
    conn.close()
    
    plt.figure(figsize=(int(len(date_range) * 0.1), 15))
    for feature, (times, values) in tqdm(items):
        plt.plot(times, values, label=feature)
    labels_time, ticks_time = zip(*sorted(time_ticks))
    plt.xticks(ticks_time, labels_time, rotation='vertical')
    plt.legend()
    plt.savefig('static/diagram.png')    
    
    return flask.render_template('number.html')  

# Executes on startup
TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
TIME_FORMAT_SHORT = "%Y-%m-%d %Hh"
start_date = datetime.datetime.strptime("2024-08-01 00:00:00.0", TIME_FORMAT)
end_date = datetime.datetime.strptime("2024-09-01 00:00:00.0", TIME_FORMAT)
DELAY = 3600
extra_points = [
    '2024-08-22 18:46:01.017058'
]
gap_times = [
    ('2024-11-10 00:00:00.000000', '2024-11-11 00:00:00.000000'),
    ('2024-11-22 00:00:00.000000', '2024-11-25 00:00:00.000000'),
]
date_range = [start_date + datetime.timedelta(hours=x)
                  for x in range(0, int((end_date - start_date).total_seconds() / 3600), DELAY // 3600)]

gaps = dict(zip(map(lambda x: x.replace(second=0, microsecond=0), date_range), [False] * len(date_range)))
for start, end in gap_times:
    start = datetime.datetime.strptime(start, TIME_FORMAT)
    end = datetime.datetime.strptime(end, TIME_FORMAT)
    if start < start_date or start > end_date:
        continue
    while start < end:
        if start not in gaps:
            print('Value not in dict:', start)
        gaps[start] = True
        start += datetime.timedelta(seconds=DELAY)
gaps = list(gaps.values())

mappings = dict()
for file in scandir('../../mappings'):
    if not file.name.endswith('.yaml'):
        continue
    with open(file, 'r') as fin:
        obj = yaml.safe_load(fin)
        mappings.update(util.update_names(obj))
mappings_extra = dict()
for file in scandir('../../mappings/other'):
    with open(file, 'r') as fin:
        obj = yaml.safe_load(fin)
        mappings_extra.update(obj)
util.set_mappings(mappings, mappings_extra)

conn = sqlite3.connect('../diff_v2_aug.sqlite3')
cur = conn.cursor()

cur.execute('SELECT DISTINCT Device, ObjectType, ObjectId, Property FROM FullValues WHERE Timestamp BETWEEN ? AND ?', (start_date, end_date))
features = cur.fetchall()

print('Loading fast_fetch', flush=True)
series.load_fast(file='../pickles/series_full.pickle')
print('Loading done', flush=True)

conn.close()

features_by_type = dict()
for elem in features:
    _, obj, _, prop = elem
    if prop == 'presentValue':
        continue
    if prop in mappings[obj]:
        typ = mappings[obj][prop]['Type']
        if type(typ) == dict and typ['Name'] in ['list', 'array', 'object', 'object ref']:
            typ = typ['Name']
        elif typ not in ['number', 'bool', 'datetime', 'other']:
            print('Found type', mappings[obj][prop]['Type'])
            continue
        if typ not in features_by_type:
            features_by_type[typ] = []
        features_by_type[typ].append(elem)
