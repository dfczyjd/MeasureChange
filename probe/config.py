import typing
import ipaddress
import random
import pathlib
import time

IPAddressString = typing.NewType("IPAddressString", str)

### LOG
log_level = 'info'

probe_ip: IPAddressString = "192.168.0.1"  # the IP address of the probing server

ip_whitelist: list[IPAddressString] = []  # list of IP addresses to query
ip_whitelist.append([str(i) for i in ipaddress.IPv4Network("192.168.0.0/24")][1:-1])  # without net and broadcast address
ip_whitelist.append([str(i) for i in ipaddress.IPv4Network("192.168.1.0/24")][1:-1])  # without net and broadcast address

###########################################################################
#ip_whitelist = random.sample(ip_whitelist, 15)  # TODO TAKE 15 random samples from the full IP list FOR TESTING PURPOSE
###########################################################################


### Delays
property_delay = 0.2  # seconds between two properties on the same device
device_delay = 0.2  # seconds between probes to two different devices
discovery_delay = 0.1  # seconds between discovery probes to different devices

# Maximum number of properties to query in a single readMultiple request
property_batch_size = 15
# Maximum number of bytes to read in a single ReadFile request to stream access file
stream_batch_size = 1024
# Maximum number of records to read in a single ReadFile request to record access file
record_batch_size = 10

### Output filenames
# Base directory for data files
base_dir = 'data'
# Database to store results and exceptions ({} will be replaced by creation date)
db_file = '{}.sqlite3'
# Template to initialize database
db_base_file = 'base.sqlite3'
# Text output file for cases, when writing to database failed
output_filename = pathlib.Path.home() / "vasily_results" / f"data{time.strftime('%Y%m%dT%H%M', time.localtime())}_localtime.txt"
output_filename = output_filename.as_posix()
