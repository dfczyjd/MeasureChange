import sqlite3
from tqdm import tqdm
import os

main_db = sqlite3.connect('diff_v2.sqlite3', isolation_level='EXCLUSIVE')
main_cur = main_db.cursor()

last_values = dict()

for file in tqdm(os.listdir('data'), position=0):
    if not file.endswith('.sqlite3'):
        continue
    conn = sqlite3.connect('data/' + file, isolation_level='EXCLUSIVE')
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT Timestamp FROM Files')    
    times = cur.fetchall()
    for time in tqdm(times, position=1, leave=False):
        time = time[0]
        cur.execute('SELECT Device, FileId, Data FROM Files WHERE Timestamp = ?', (time,))
        snap = cur.fetchall()
        for elem in tqdm(snap, position=2, leave=False):
            key, value = elem[:-1], elem[-1]
            if key not in last_values:
                last_values[key] = (value, time)
                continue
            if last_values[key][0] == value:
                continue
            main_cur.execute('INSERT INTO Files (Timestamp, Device, FileId, Data) VALUES (?, ?, ?, ?)',
                             (last_values[key][1],) + key + (last_values[key][0],))    
            print('Found diff', flush=True)
            last_values[key] = (value, time)
    main_db.commit()
    conn.close()

main_db.close()