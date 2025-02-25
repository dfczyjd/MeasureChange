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

ip_blacklist: list[IPAddressString] = [] # list of IP addresses to skip
ip_blacklist += [
    # Removed
]


### Delays
property_delay = 0.2  # seconds between two properties on the same device
device_delay = 0.2  # seconds between probes to two different devices
discovery_delay = 0.1  # seconds between discovery probes to different devices

# Maximum number of bytes to read in a single ReadFile request to stream access file
stream_batch_size = 1024
# Maximum number of records to read in a single ReadFile request to record access file
record_batch_size = 10
# Size threshold for stream access file in bytes to be considered large and skipped
large_stream_file_size = 10485760
# Size threshold for record access file in records to be considered large and skipped
large_record_file_size = 10000

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

# Set to True to enable packet capture
enable_capture = True
# File to write packets to
capture_output_file = 'capture.pcap'
# List of IP addresses to capture packets from/to
capture_target_ip = ['192.168.183.1']
