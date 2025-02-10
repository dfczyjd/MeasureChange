import sqlite3
import datetime
from tqdm import tqdm

conn = sqlite3.connect('diff_v2.sqlite3')
cur = conn.cursor()

TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
TIME_FORMAT_SHORT = "%Y-%m-%d %Hh"
start_date = datetime.datetime.strptime("2024-11-01 00:00:00.000000", TIME_FORMAT)
end_date = datetime.datetime.strptime("2024-12-01 00:00:00.000000", TIME_FORMAT)

cur.execute('SELECT DISTINCT Timestamp, Device, ObjectType, ObjectId, Property, Value FROM FullValues WHERE Timestamp BETWEEN ? AND ?', (start_date, end_date))
data = cur.fetchall()

conn.close()

conn = sqlite3.connect('diff_v2_nov.sqlite3')
cur = conn.cursor()

for elem in tqdm(data):
    cur.execute('INSERT INTO FullValues (Timestamp, Device, ObjectType, ObjectId, Property, Value) VALUES (?, ?, ?, ?, ?, ?)', elem)
conn.commit()

conn.close()