python3 device.py --ini BACpypes1.ini &
dev1=$!
python3 device.py --ini BACpypes2.ini &
dev2=$!
python3 probe.py
kill -n 2 $dev1 $dev2
