import zlib
import os
from tqdm import tqdm
import shutil

"""
ips = []
for file in os.listdir('logs'):
    with open('logs/' + file, 'r') as fin:
        lines = fin.readlines()
        last_int = -1
        last = ''
        last_line = ''
        for line in lines:
            time = line.split()[2]
            h, m, s = time.split(':')
            time_int = int(h) * 3600 + int(m) * 60 + int(s)
            if last_int > 0 and time_int - last_int >= 60 * 5:
                print(f'{last} - {time}: {last_line}', end='')
                if 'Prossess' in line and "'" not in line:
                    ips.append(line.split()[-1].split(':')[0])
            last_int = time_int
            last = time
            last_line = line

print(*sorted(set(ips)), sep='\t\n')
"""
for file in tqdm(os.listdir('.')):
    if not file.endswith('.zip'):
        continue
    with open(file, 'rb') as fin:
        data = fin.read()
        with open(file[:-4], 'wb') as fout:
            fout.write(zlib.decompress(data))
    shutil.move(file, 'zips/' + file)
#"""