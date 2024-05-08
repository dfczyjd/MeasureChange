import typing
import ipaddress
import random
import pathlib
import time

IPAddressString = typing.NewType("IPAddressString", str)

### LOG
log_level = 'info'

probe_ip: IPAddressString = "192.168.183.2"  # the IP address of the probing server

ip_whitelist: list[IPAddressString] = []  # list of IP addresses to query
ip_whitelist = ['192.168.183.1', '192.168.183.3']
#ip_whitelist.append([str(i) for i in ipaddress.IPv4Network("192.168.0.0/24")][1:-1])  # without net and broadcast address
#ip_whitelist.append([str(i) for i in ipaddress.IPv4Network("192.168.1.0/24")][1:-1])  # without net and broadcast address

###########################################################################
#ip_whitelist = random.sample(ip_whitelist, 15)  # TODO TAKE 15 random samples from the full IP list FOR TESTING PURPOSE
###########################################################################


### Delays
property_delay = 0.002  # seconds between two properties on the same device
device_delay = 0.002  # seconds between probes to two different devices
discovery_delay = 0.001  # seconds between discovery probes to different devices

# Output filenames
output_filename = "data.txt"
