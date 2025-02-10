import sqlite3
from tqdm import tqdm

"""
conn1 = sqlite3.connect('2024-11-11.sqlite3')
conn2 = sqlite3.connect('2024-11-11_PART_2.sqlite3')
cur1 = conn1.cursor()
cur2 = conn2.cursor()

cur2.execute('SELECT * FROM PropertyValues')
data = cur2.fetchall()
conn2.close()

for elem in tqdm(data):
    cur1.execute('INSERT INTO PropertyValues (Timestamp, Device, ObjectType, ObjectId, Property, Value) VALUES (?, ?, ?, ?, ?, ?)', elem[1:])

conn1.commit()
conn1.close()
"""

conn1 = sqlite3.connect('../diff_v2.sqlite3')
cur1 = conn1.cursor()

dbs = ['../diff_v2_aug.sqlite3', '../diff_v2_sep.sqlite3', '../diff_v2_oct.sqlite3', '../diff_v2_nov.sqlite3']

for db in dbs:
    conn2 = sqlite3.connect(db)
    cur2 = conn2.cursor()
    
    cur2.execute('SELECT * FROM ListSeries')
    data = cur2.fetchall()
    
    conn2.close()
    
    for elem in tqdm(data):
        cur1.execute('INSERT INTO ListSeries (Feature, Timestamp, ItemId, Value, Color) VALUES (?, ?, ?, ?, ?)', elem)
    
    conn1.commit()

conn1.close()