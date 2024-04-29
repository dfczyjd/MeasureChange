import yaml
import os

data = []

for elem in os.listdir():
    if elem[-5:] != '.yaml':
        continue
    with open(elem, 'r') as fin:
        loader = yaml.loader.Loader(fin)
        item = loader.get_data()
        data += item

categories = [
    'Process Input Variable',
    'Process Output Variable',
    'Process Configuration Parameter',
    'Process Control Variable',
    'Monitoring Pull Configuration',
    'Monitoring Push Configuration',
    'Alarm Condition',
    'Alarm Priority',
    'Alarm Suppression',
    'Alarm Ack Required',
    'Device Diagnostics',
    'Device Control',
    'Device Configuration',
    'Human Info'
]
actions = [
    'add/delete',
    'config change',
    'activate/deactivate',
    'value change',
    'override',
    'tighten/relax'
]
tbl = [
    '***.*.',
    '***.*.',
    '**.*..',
    '**.*..',
    '..*..*',
    '..*..*',
    '*.*..*',
    '...*..',
    '..*...',
    '...*..',
    '**....',
    '**.*..',
    '**.*..',
    '**.*..',
]
tbl = [[x == '*' for x in line] for line in tbl]

total = dict()
for elem in categories:
    total[elem] = set()
    
have_table = [[0] * len(actions) for i in range(len(categories))]
for i in range(len(categories)):
    for j in range(len(actions)):
        if tbl[i][j]:
            have_table[i][j] = 1

for obj in data:
    attr_list = list(obj.values())[0]
    for attr in attr_list:
        attr_value = list(attr.values())[0]
        for category in attr_value:
            if category not in categories or attr_value[category] is None:
                continue
            acts = attr_value[category]['Actions']
            total[category].update(acts)
            cat_ind = categories.index(category)
            for act in acts:
                if act not in actions:
                    continue
                act_ind = actions.index(act)
                if tbl[cat_ind][act_ind]:
                    have_table[cat_ind][act_ind] = 2

maxlen_cat = max([len(x) for x in categories])
maxlen_act = max([len(x) for x in actions])

for i in range(maxlen_act):
    print(' ' * (maxlen_cat + 2), end='')
    for act in actions:
        if i >= maxlen_act - len(act):
            print(act[i - maxlen_act + len(act)], end='  ')
        else:
            print('   ', end='')
    print()

for i, line in enumerate(have_table):
    print(' ' * (maxlen_cat - len(categories[i])) + categories[i], end='  ')
    for elem in line:
        sym = ' '
        if elem == 1:
            sym = '-'
        elif elem == 2:
            sym = '+'
        print(sym, end='  ')
    print()

"""
for elem in total:
    print(elem + ':')
    for elem2 in total[elem]:
        print('\t' + elem2)
"""