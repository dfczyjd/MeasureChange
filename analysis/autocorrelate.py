import sqlite3
from tqdm import tqdm
import datetime
import pandas as pd
from statsmodels.graphics.tsaplots import plot_acf
import numpy as np

import util

def expand_series(timestamps, values):
    global start_date, end_date, date_range
    res = []
    values = list(values)
    timestamps = list(map(lambda t: datetime.datetime.strptime(t, TIME_FORMAT), timestamps))
    if timestamps[0] != start_date:
        print(timestamps[0], start_date)
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

def autocorr(x):
    result = np.correlate(x, x, mode='full')
    return result[result.size//2:]

conn = sqlite3.connect('diff_v2.sqlite3')
cur = conn.cursor()

query = '''SELECT Timestamp, Value FROM FullValues
	WHERE Device == <REDACTED>
	AND ObjectType == <REDACTED>
	AND ObjectId == <REDACTED>
	AND Property == <REDACTED>
	ORDER BY Timestamp'''

cur.execute(query)
data = cur.fetchall()
conn.close()

TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
TIME_FORMAT_SHORT = "%Y-%m-%d %Hh"
start_date = datetime.datetime.strptime("2024-08-02 12:00:00.0", TIME_FORMAT)
end_date = datetime.datetime.strptime("2024-12-01 00:00:00.0", TIME_FORMAT)
DELAY = 3600
date_range = [start_date + datetime.timedelta(hours=x)
                  for x in range(0, int((end_date - start_date).total_seconds() / 3600), DELAY // 3600)]

timestamps, values = zip(*data)
function = pd.DataFrame(util.enumerate_series(expand_series(timestamps, values), [False] * 10000))

items = []
for i in range(2, len(date_range) // 2):
    df = pd.concat([function, function.shift(i)], axis=1)
    corr = df.corr().iloc[0, 1]
    if not np.isnan(corr):
        items.append((corr, i))
items.sort()
print(*items[-5:], sep='\n')