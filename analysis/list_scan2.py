import sqlite3
from tqdm import tqdm
import datetime

import series
import util
import device_ids

conn = sqlite3.connect('diff_v2.sqlite3')
cur = conn.cursor()

obj = 'device'
prop = 'deviceAddressBinding'

cur.execute(f'''SELECT ObjectId FROM FullValues
	WHERE Property == '{prop}'
	--AND Timestamp NOT BETWEEN '2024-11-13 08:00' AND '2024-11-13 11:00'
	GROUP BY ObjectId
	HAVING COUNT(DISTINCT Value) > 1''')
feats = cur.fetchall()

TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

res = []
for obj in tqdm(feats):
    cur.execute(f"SELECT Timestamp, Value FROM FullValues WHERE ObjectId == ? AND Property == '{prop}'", obj)
    times, vals = zip(*cur.fetchall())
    values = []
    for i, elem in enumerate(vals):
        val = util.parse_list(elem)
        if val is not None:
            val = series.remove_duplicates(None, val)
        if len(values) == 0:
            values.append(val)
            continue
        if values[-1] == []:
            time_curr, time_prev = times[i], times[i - 1]
            time_curr = datetime.datetime.strptime(time_curr, TIME_FORMAT).replace(second=0, microsecond=0)
            time_prev = datetime.datetime.strptime(time_prev, TIME_FORMAT).replace(second=0, microsecond=0)
            if (time_curr - time_prev).total_seconds() <= 7200: # 2 hours
                values.pop()
        if val != values[-1]:
            values.append(val)
    if len(values) > 1:
        res.append(obj[0])
print(len(res))
input()
print(*res, sep='\n')

conn.close()