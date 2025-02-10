import sqlite3
from tqdm import tqdm
import datetime

import device_ids

conn = sqlite3.connect('diff_v2.sqlite3')
cur = conn.cursor()

cur.execute('SELECT * FROM ListSeries WHERE Color != "black" ORDER BY ItemId')
data = cur.fetchall()

for i in range(len(data)):
    feat = data[i][0].split(':')
    feat = str(device_ids.get_id(feat[0])) + ':' + ':'.join(feat[1:])
    data[i] = (feat,) + tuple(data[i][1:])

data.sort(key=lambda x: (x[0], x[2]))

prev = None
add = []
rem = []
res = dict()
longs = dict()
TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
for elem in data:
    feat, time, item_id, value, color = elem
    
    if prev != feat:
        if add != rem:
            add_diff = []
            rem_diff = []
            add.sort(key=lambda x: x[1])
            rem.sort(key=lambda x: x[1])
            i1 = 0
            i2 = 0
            while i1 < len(add) and i2 < len(rem):
                val1 = add[i1][1]
                val2 = rem[i2][1]
                if val1 == val2:
                    diff = datetime.datetime.strptime(add[i1][0], TIME_FORMAT) - datetime.datetime.strptime(rem[i2][0], TIME_FORMAT)
                    if abs(diff.total_seconds()) >= 60 * 60 * 24 * 5:
                        print(diff)
                        longs[prev] = add[i1][0], rem[i2][0], val1
                    i1 += 1
                    i2 += 1
                elif val1 < val2:
                    add_diff.append(add[i1])
                    i1 += 1
                else:
                    rem_diff.append(rem[i1])
                    i2 += 1
            if len(add_diff) + len(rem_diff) > 0:
                res[prev] = (add_diff, rem_diff)
        add = []
        rem = []
        prev = feat
    value = '\n'.join(value.split('\n')[:-1])
    if color == 'red':
        rem.append((time, value))
    else:
        add.append((time, value))
add.sort()
rem.sort()
if add != rem:
    i1 = 0
    i2 = 0
    while i1 < len(add) and i2 < len(rem):
        if add[i1] == rem[i2]:
            i1 += 1
            i2 += 1
        elif add[i1] < rem[i2]:
            add_diff.append(add[i1])
            i1 += 1
        else:
            rem_diff.append(rem[i1])
            i2 += 1
    if len(add_diff) + len(rem_diff) > 0:
        res[prev] = (add_diff, rem_diff)    

for key in res:
    add, rem = res[key]
    changes = [(x[0], x[1], 'green') for x in add]
    changes += [(x[0], x[1], 'red') for x in rem]
conn.commit()

print('Total devices:', len(res))
cnt = 0
cnt_add = 0
cnt_add_ch = 0
with open('output.txt', 'w') as fout:
    for key in res:
        print(key, file=fout)
        add, rem = res[key]
        print('  Added:', file=fout)
        cnt += len(add) + len(rem)
        if len(add) > 0:
            cnt_add += 1
            cnt_add_ch += len(add)
        for time, value in add:
            print('    ' + str(time), file=fout)
            print(value, file=fout)
        print('  Removed:', file=fout)
        for time, value in rem:
            print('    ' + str(time), file=fout)
            print(value, file=fout)
print('Total changes:', cnt)
print('Devices with adding:', cnt_add)
print('Changes with adding:', cnt_add_ch)

inter = []
TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
lower = datetime.datetime.strptime("2024-11-13 19:00:02.171600", TIME_FORMAT)
upper = datetime.datetime.strptime("2024-09-01 00:00:00.0", TIME_FORMAT)

for key in res:
    add, rem = res[key]
    for time, val in rem:
        time = datetime.datetime.strptime(time, TIME_FORMAT)
        if time >= lower:
            print(key, time)
            inter.append(key)
            break
print('Interesting count:', len(inter))

conn.close()
