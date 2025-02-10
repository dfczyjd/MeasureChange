import sqlite3
import pickle

def get_id(ip):
    global ids
    if ip.startswith('192.'):
        return ids[ip]
    return ip

if __name__ == '__main__':
    # Collect and store the mapping
    conn = sqlite3.connect('diff_v2_nov.sqlite3')
    cur = conn.cursor()
    cur.execute('''
    SELECT DISTINCT Device, ObjectId FROM FullValues
	WHERE Device LIKE '192.168.%'
	AND ObjectType = 'device'
    ''')
    data = cur.fetchall()
    res = dict(data)
    with open('device_ids.pickle', 'wb') as fout:
        pickle.dump(res, fout)
    conn.close()
else:
    # Script is invoked as a submodule, load the data
    print('Loading ips', flush=True)
    with open('device_ids.pickle', 'rb') as fin:
        ids = pickle.load(fin)