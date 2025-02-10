import sqlite3
from tqdm import tqdm
import yaml
from os import scandir

import series
import util

db = sqlite3.connect('diff_v2.sqlite3')
cur = db.cursor()
cur.execute('DELETE FROM FullValues WHERE 1=1')

cur.execute('SELECT Timestamp, Device, ObjectType, ObjectId, Property, Value FROM PropertyValues')
data = cur.fetchall()
print('First done', flush=True)
cur.execute('SELECT Timestamp, Device, ObjectType, ObjectId, Property, Value FROM LastValues')
data += cur.fetchall()
print('Second done', flush=True)
data.sort()


for i, elem in enumerate(tqdm(data)):
    if i > 0 and data[i - 1] == elem:
        continue
    cur.execute('INSERT INTO FullValues (Timestamp, Device, ObjectType, ObjectId, Property, Value) VALUES (?, ?, ?, ?, ?, ?)', elem)

db.commit()
db.close()